import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.erp.stock import inspect_received_goods
from eorl_lab.organization.communication import message_agent
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.runtime import authority
from eorl_lab.runtime.orchestrator import run_architecture

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {"may_submit_documents": 0, "tools": ["get_supplier_options", "create_purchase_order"]},
	"purchasing_manager_agent": {"may_submit_documents": 1, "tools": ["get_purchase_order", "submit_purchase_order"]},
	"warehouse_agent": {
		"may_submit_documents": 1,
		"may_message_agents": 1,
		"tools": [
			"get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt",
			"inspect_received_goods", "escalate_quality_exception", "message_agent",
		],
	},
	"accounts_payable_agent": {
		"may_submit_documents": 1,
		"tools": [
			"get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice",
			"create_payment_entry", "submit_payment_entry",
		],
	},
}
SPECIALIST_ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent",
	"purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent",
	"accounts_payable_agent": "Accounts Payable Agent",
}


class TestGroundTruthAndAuthority(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile SOTA1",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		self.communication_policy = frappe.get_doc(
			{
				"doctype": "EORL Communication Policy",
				"policy_name": "Test Procurement Communication Policy SOTA1",
				"edges": [
					{"from_slot": "Warehouse Agent", "to_slot": "Accounts Payable Agent", "allowed": 1},
				],
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy SOTA1",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} SOTA1",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})

		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff SOTA1",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
				"communication_policy": self.communication_policy.name,
			}
		).insert(ignore_if_duplicate=True)

	# --- Ground truth actually drives outcomes (V2 section 15) ---

	def test_inspection_result_is_forced_by_ground_truth_not_scripted(self):
		"""Calls the tool directly against a real Purchase Receipt, with
		a crafted `_case` -- proves the SAME function call produces
		opposite outcomes purely because the ground truth differs, not
		because any code branch was toggled."""
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": "Bloomington Dairy",
				"company": "Hoosier Ice Cream",
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
				"items": [
					{
						"item_code": "MILK-001", "qty": 100, "rate": 1,
						"warehouse": "Stores - HIC", "schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
					}
				],
			}
		).insert()
		po.submit()
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.insert()

		always_fail_case = {"latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.0}}, "case_hash": "force-fail"}
		always_pass_case = {"latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 1.0}}, "case_hash": "force-pass"}

		fail_result = inspect_received_goods(pr.name, _case=always_fail_case)
		self.assertFalse(fail_result["quality_passed"])
		self.assertGreater(fail_result["units_rejected"], 0)

		pass_result = inspect_received_goods(pr.name, _case=always_pass_case)
		self.assertTrue(pass_result["quality_passed"])
		self.assertEqual(pass_result["units_rejected"], 0)

	def test_inspection_is_deterministic_given_the_same_case_hash(self):
		po = frappe.get_doc(
			{
				"doctype": "Purchase Order",
				"supplier": "Bloomington Dairy",
				"company": "Hoosier Ice Cream",
				"schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
				"items": [
					{
						"item_code": "MILK-001", "qty": 100, "rate": 1,
						"warehouse": "Stores - HIC", "schedule_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
					}
				],
			}
		).insert()
		po.submit()
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

		pr = make_purchase_receipt(po.name)
		pr.insert()

		case = {"latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.5}}, "case_hash": "repeatable-hash"}
		first = inspect_received_goods(pr.name, _case=case)
		second = inspect_received_goods(pr.name, _case=case)
		self.assertEqual(first["quality_passed"], second["quality_passed"])

	def test_quality_outcome_is_consistent_with_the_full_event_trace(self):
		"""End-to-end through the real orchestrator (no forced ground
		truth -- whatever the seed happens to draw): whichever branch
		occurred, the event trace must be self-consistent with it."""
		result = run_architecture(self.specialist_architecture.name, seed=7, episode_count=1)
		self.assertTrue(result["outcome"]["success"], result["outcome"].get("failure_reason"))

		target_ids = [
			e.target_id for e in frappe.get_all("EORL Event", filters={"run": result["run"]}, fields=["target_id"])
		]
		self.assertIn("inspect_received_goods", target_ids)

		if result["outcome"]["quality_passed"]:
			self.assertNotIn("escalate_quality_exception", target_ids)
		else:
			self.assertIn("escalate_quality_exception", target_ids)
			self.assertIn("message_agent", target_ids)

	# --- Decision-tree branching, isolated from the orchestrator/DB ---

	def test_warehouse_decision_tree_branches_on_quality_outcome(self):
		provider = DeterministicProvider()

		passed_context = {
			"organizational_role": "Warehouse Agent",
			"handoff": {"purchase_order": "PO-X"},
			"scratch": {"purchase_order_status": "Submitted", "purchase_receipt": "PR-X", "quality_passed": True},
			"memory": [],
		}
		decision = provider._decide_warehouse_agent(passed_context)
		self.assertEqual(decision["intended_action"], "submit_purchase_receipt")

		failed_context = {
			"organizational_role": "Warehouse Agent",
			"handoff": {"purchase_order": "PO-X"},
			"scratch": {
				"purchase_order_status": "Submitted", "purchase_receipt": "PR-X",
				"quality_passed": False, "units_rejected": 3,
			},
			"memory": [],
		}
		self.assertEqual(provider._decide_warehouse_agent(failed_context)["intended_action"], "escalate_quality_exception")

		failed_context["scratch"]["quality_exception_escalated"] = True
		self.assertEqual(provider._decide_warehouse_agent(failed_context)["intended_action"], "message_agent")

		failed_context["scratch"]["delivered"] = False  # message attempted, whether or not it was deliverable
		self.assertEqual(provider._decide_warehouse_agent(failed_context)["intended_action"], "submit_purchase_receipt")

	# --- Agent-chosen communication, checked against a real policy graph ---

	def test_message_agent_delivers_only_where_the_policy_allows_it(self):
		delivered = message_agent(
			"Accounts Payable Agent", "test content",
			_sender_slot="Warehouse Agent", _communication_policy=self.communication_policy.name,
		)
		self.assertTrue(delivered["delivered"])

		blocked = message_agent(
			"Purchasing Manager Agent", "test content",  # no edge to this recipient
			_sender_slot="Warehouse Agent", _communication_policy=self.communication_policy.name,
		)
		self.assertFalse(blocked["delivered"])
		self.assertEqual(blocked["reason"], "NO_COMMUNICATION_EDGE")

		no_policy = message_agent(
			"Accounts Payable Agent", "test content", _sender_slot="Warehouse Agent", _communication_policy=None,
		)
		self.assertFalse(no_policy["delivered"])
		self.assertEqual(no_policy["reason"], "NO_POLICY_BOUND")

	def test_message_agent_requires_may_message_agents_authority(self):
		no_messaging_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test No Messaging Policy SOTA1",
				"may_message_agents": 0,
				"allowed_semantic_tools": [{"tool_name": "message_agent"}],
			}
		).insert(ignore_if_duplicate=True)

		decision = authority.evaluate(
			tool_policy_name=no_messaging_policy.name, tool_name="message_agent", tool_args={},
		)
		self.assertFalse(decision.allowed)
		self.assertEqual(decision.reason_code, "MESSAGING_NOT_PERMITTED")

	# --- Hard constraints still block; soft rules log but never block ---

	def test_soft_rule_logs_without_blocking(self):
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Soft Rule Policy SOTA1",
				"soft_rule_large_qty_threshold": 500,
				"allowed_semantic_tools": [{"tool_name": "create_purchase_order"}],
			}
		).insert(ignore_if_duplicate=True)

		small_order = authority.evaluate(
			tool_policy_name=policy.name, tool_name="create_purchase_order", tool_args={"qty": 100},
		)
		self.assertTrue(small_order.allowed)
		self.assertEqual(small_order.soft_violations, [])

		large_order = authority.evaluate(
			tool_policy_name=policy.name, tool_name="create_purchase_order", tool_args={"qty": 1000},
		)
		self.assertTrue(large_order.allowed, "a soft rule must never block execution")
		self.assertIn("large_order_requires_manager_preapproval", large_order.soft_violations)

	def test_soft_rule_violation_is_logged_as_its_own_event_when_triggered(self):
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Soft Rule Policy SOTA1 Live",
				"may_submit_documents": 0,
				"soft_rule_large_qty_threshold": 1,  # guaranteed to trigger for our demo case's qty
				"allowed_semantic_tools": [{"tool_name": "get_supplier_options"}, {"tool_name": "create_purchase_order"}],
			}
		).insert(ignore_if_duplicate=True)
		agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Soft Rule Purchasing Agent SOTA1",
				"organizational_role": "Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": policy.name,
			}
		).insert(ignore_if_duplicate=True)

		from eorl_lab.runtime.orchestrator import run_demo_episode

		result = run_demo_episode(agent.name, seed=1)
		self.assertTrue(result["outcome"]["success"])

		soft_events = frappe.get_all(
			"EORL Event", filters={"run": result["run"], "event_type": "soft_rule_violation"}, fields=["payload_json"],
		)
		self.assertEqual(len(soft_events), 1)
		self.assertIn("large_order_requires_manager_preapproval", frappe.parse_json(soft_events[0].payload_json)["violations"])

	def test_hard_constraint_still_blocks_regardless_of_soft_rules(self):
		"""Soft rules are additive, not a replacement for the hard
		constraint path (V2 section 13: the two are independent)."""
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Hard Plus Soft Policy SOTA1",
				"soft_rule_large_qty_threshold": 1,
				"allowed_semantic_tools": [{"tool_name": "get_supplier_options"}],  # create_purchase_order NOT allowed
			}
		).insert(ignore_if_duplicate=True)
		decision = authority.evaluate(
			tool_policy_name=policy.name, tool_name="create_purchase_order", tool_args={"qty": 1000},
		)
		self.assertFalse(decision.allowed)
		self.assertEqual(decision.reason_code, "TOOL_NOT_IN_POLICY")

	# --- Authority model fields persist (V2 section 12's four types) ---

	def test_authority_type_fields_persist_independently(self):
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Authority Types Policy SOTA1",
				"has_execution_authority": 1,
				"has_decision_authority": 1,
				"may_approve": 0,
				"has_assignment_authority": 1,
			}
		).insert(ignore_if_duplicate=True)
		reloaded = frappe.get_doc("EORL Tool Policy", policy.name)
		self.assertTrue(reloaded.has_decision_authority)
		self.assertFalse(reloaded.may_approve)
		self.assertTrue(reloaded.has_assignment_authority)

	# --- Process Grammar is queryable and consistent with the default map ---

	def test_process_grammar_resolves_to_a_stage_map_matching_the_default(self):
		grammar = frappe.get_doc(
			{
				"doctype": "EORL Process Grammar",
				"grammar_name": "Test Procure To Pay Grammar SOTA1",
				"stages": [
					{"stage_id": "SUPPLIER_SEARCH", "label": "Supplier Search"},
					{"stage_id": "PURCHASE_ORDER", "label": "Purchase Order"},
					{"stage_id": "APPROVAL", "label": "Approval"},
					{"stage_id": "RECEIPT", "label": "Receipt"},
					{"stage_id": "EXCEPTION", "label": "Exception"},
					{"stage_id": "INVOICE", "label": "Invoice"},
					{"stage_id": "PAYMENT", "label": "Payment", "is_terminal": 1},
				],
				"transitions": [
					{"to_stage": "SUPPLIER_SEARCH", "tool_names": "get_supplier_options"},
					{"to_stage": "PURCHASE_ORDER", "tool_names": "create_purchase_order, get_purchase_order"},
					{"to_stage": "APPROVAL", "tool_names": "submit_purchase_order"},
					{"to_stage": "RECEIPT", "tool_names": "create_purchase_receipt, submit_purchase_receipt, get_receipt_status, inspect_received_goods"},
					{"to_stage": "EXCEPTION", "tool_names": "escalate_quality_exception"},
					{"to_stage": "INVOICE", "tool_names": "create_purchase_invoice, submit_purchase_invoice"},
					{"to_stage": "PAYMENT", "tool_names": "create_payment_entry, submit_payment_entry"},
				],
			}
		).insert(ignore_if_duplicate=True)

		from eorl_lab.analysis.paths import PROCESS_STAGE_BY_TOOL

		resolved = grammar.to_stage_map()
		fixture_stages = {row.stage_id for row in grammar.stages}
		for tool_name, expected_stage in PROCESS_STAGE_BY_TOOL.items():
			if tool_name == "message_agent":
				continue  # deliberately not modeled in this grammar fixture
			if expected_stage not in fixture_stages:
				continue  # finish_turn (CONTROL) and the order-to-cash tools belong to other grammars
			self.assertEqual(resolved.get(tool_name), expected_stage, tool_name)

	def test_process_path_extraction_accepts_a_custom_stage_map(self):
		from eorl_lab.analysis.paths import process_path

		events = [
			{"event_type": "tool_result", "target_id": "get_supplier_options", "actor_slot": "Purchasing Agent", "success": 1},
			{"event_type": "tool_result", "target_id": "create_purchase_order", "actor_slot": "Purchasing Agent", "success": 1},
		]
		custom_map = {"get_supplier_options": "SOURCING", "create_purchase_order": "ORDERING"}
		self.assertEqual(process_path(events, stage_map=custom_map), ["SOURCING:get_supplier_options", "ORDERING:create_purchase_order"])
		# Default map still works unchanged when no override is given.
		self.assertEqual(
			process_path(events),
			["SUPPLIER_SEARCH:get_supplier_options", "PURCHASE_ORDER:create_purchase_order"],
		)

	# --- Task assignment is a real, logged decision (V2 section 11) ---

	def test_task_assignment_recorded_for_every_role_every_episode(self):
		result = run_architecture(self.specialist_architecture.name, seed=3, episode_count=2)
		self.assertTrue(result["outcome"]["success"])

		assignments = frappe.get_all(
			"EORL Task Assignment", filters={"run": result["run"]}, fields=["slot_id", "episode", "assignment_policy"],
		)
		# 4 roles x 2 episodes = 8 assignment records.
		self.assertEqual(len(assignments), 8)
		self.assertTrue(all(a.assignment_policy == "fixed" for a in assignments))

		task_assigned_events = frappe.get_all(
			"EORL Event", filters={"run": result["run"], "event_type": "task_assigned"},
		)
		self.assertEqual(len(task_assigned_events), 8)
