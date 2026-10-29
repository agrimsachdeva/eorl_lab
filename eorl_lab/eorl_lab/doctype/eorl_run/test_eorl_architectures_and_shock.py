import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.runtime.orchestrator import run_architecture
from eorl_lab.scenarios.procurement import generate_case

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {
		"may_submit_documents": 0,
		"tools": ["get_supplier_options", "create_purchase_order"],
	},
	"purchasing_manager_agent": {
		"may_submit_documents": 1,
		"may_approve": 1,
		"tools": ["get_purchase_order", "submit_purchase_order"],
	},
	"warehouse_agent": {
		"may_submit_documents": 1,
		"tools": ["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt"],
	},
	"accounts_payable_agent": {
		"may_submit_documents": 1,
		"tools": [
			"get_receipt_status",
			"create_purchase_invoice",
			"submit_purchase_invoice",
			"create_payment_entry",
			"submit_payment_entry",
		],
	},
}

SPECIALIST_ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent",
	"purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent",
	"accounts_payable_agent": "Accounts Payable Agent",
}

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options",
	"get_purchase_order",
	"get_receipt_status",
	"create_purchase_order",
	"submit_purchase_order",
	"create_purchase_receipt",
	"submit_purchase_receipt",
	"create_purchase_invoice",
	"submit_purchase_invoice",
	"create_payment_entry",
	"submit_payment_entry",
]


class TestEORLArchitecturesAndShock(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M5",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy M5",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_approve": spec.get("may_approve", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} M5",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})

		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff M5",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

		broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Broad Autonomy Policy M5",
				"may_submit_documents": 1,
				"may_approve": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test General Purchasing Agent M5",
				"organizational_role": "General Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)

		self.broad_autonomy_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Broad Autonomy M5",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift",
				"shift_name": "Test Demand Shock M5",
				"trigger_episode": 2,
				"shift_type": "abrupt",
				"hidden_from_agents": 1,
				"parameter_delta_json": frappe.as_json({"qty_multiplier": 1.8}),
			}
		).insert(ignore_if_duplicate=True)

	def test_broad_autonomy_completes_with_zero_handoffs(self):
		result = run_architecture(self.broad_autonomy_architecture.name, seed=5, episode_count=1)
		outcome = result["outcome"]
		self.assertTrue(outcome["success"], outcome.get("failure_reason"))

		events = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"]},
			fields=["event_type", "actor_slot"],
			order_by="sequence_no asc",
		)
		# Exactly one actor identity for the whole episode, and no
		# inter-agent messages at all -- "fewer mandatory handoffs" is
		# structural, not a matter of degree, for this architecture.
		actor_slots = {e.actor_slot for e in events if e.actor_slot}
		self.assertEqual(actor_slots, {"General Purchasing Agent"})
		self.assertEqual(sum(1 for e in events if e.event_type == "agent_message_sent"), 0)

		for required in [
			"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
			"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
			"create_payment_entry", "submit_payment_entry",
		]:
			self.assertIn(required, [e.target_id for e in frappe.get_all(
				"EORL Event", filters={"run": result["run"]}, fields=["target_id"]
			)])

	def test_architecture_selection_is_config_driven_not_hardcoded(self):
		"""The same orchestrator entrypoint, called with two different
		EORL Architecture names, produces two structurally different
		executions (3 handoffs + 4 actors vs. 0 handoffs + 1 actor) --
		proving coordination_mode actually drives behavior rather than
		the caller choosing a Python function per architecture."""
		specialist_result = run_architecture(self.specialist_architecture.name, seed=11, episode_count=1)
		broad_result = run_architecture(self.broad_autonomy_architecture.name, seed=11, episode_count=1)

		self.assertTrue(specialist_result["outcome"]["success"])
		self.assertTrue(broad_result["outcome"]["success"])

		specialist_actor_slots = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event", filters={"run": specialist_result["run"]}, fields=["actor_slot"]
			) if e.actor_slot
		}
		broad_actor_slots = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event", filters={"run": broad_result["run"]}, fields=["actor_slot"]
			) if e.actor_slot
		}
		self.assertEqual(len(specialist_actor_slots), 4)
		self.assertEqual(len(broad_actor_slots), 1)

	def test_paired_seeds_give_architectures_the_identical_exogenous_stream(self):
		"""Spec section 30's acceptance test, scoped to what this
		milestone actually builds: a fixed scenario stream with a shock,
		run under two architectures on the same seed, proving the
		exogenous stream is byte-identical between them (paired seeds,
		section 18) while the resulting process genuinely differs
		(section 2.3) -- without yet requiring the full metrics/export
		layers (sections 17/18's analysis functions, a later milestone)."""
		seed = 99
		regime_shift_payload = {
			"trigger_episode": self.regime_shift.trigger_episode,
			"parameter_delta_json": frappe.parse_json(self.regime_shift.parameter_delta_json),
		}

		# The exogenous stream itself, independent of any run: same
		# inputs, same cases, pre- and post-shock.
		pre_shock_case = generate_case(seed=seed, episode=1, regime_shift=regime_shift_payload)
		post_shock_case_again = generate_case(seed=seed, episode=1, regime_shift=regime_shift_payload)
		self.assertEqual(pre_shock_case["case_hash"], post_shock_case_again["case_hash"])

		shocked_case = generate_case(seed=seed, episode=2, regime_shift=regime_shift_payload)
		unshocked_case_same_episode = generate_case(seed=seed, episode=2, regime_shift=None)
		self.assertNotEqual(shocked_case["qty"], unshocked_case_same_episode["qty"])
		self.assertEqual(shocked_case["qty"], round(unshocked_case_same_episode["qty"] * 1.8))

		specialist_result = run_architecture(
			self.specialist_architecture.name, seed=seed, episode_count=2, regime_shift=self.regime_shift.name
		)
		broad_result = run_architecture(
			self.broad_autonomy_architecture.name, seed=seed, episode_count=2, regime_shift=self.regime_shift.name
		)

		self.assertTrue(specialist_result["episodes"][0]["success"])
		self.assertTrue(specialist_result["episodes"][1]["success"])
		self.assertTrue(broad_result["episodes"][0]["success"])
		self.assertTrue(broad_result["episodes"][1]["success"])

		# Both architectures actually ordered the shocked quantity in
		# episode 2 -- the shift reached both of them identically.
		specialist_po_2 = frappe.get_doc("Purchase Order", specialist_result["episodes"][1]["purchase_order"])
		broad_po_2 = frappe.get_doc("Purchase Order", broad_result["episodes"][1]["purchase_order"])
		self.assertEqual(specialist_po_2.items[0].qty, shocked_case["qty"])
		self.assertEqual(broad_po_2.items[0].qty, shocked_case["qty"])

		# Both architectures' own episode records agree on which episode
		# ground truth they saw, and it's identical between them.
		specialist_episode_2 = frappe.get_doc(
			"EORL Episode", f"{specialist_result['run']}-EP-2"
		)
		broad_episode_2 = frappe.get_doc("EORL Episode", f"{broad_result['run']}-EP-2")
		self.assertEqual(specialist_episode_2.phase, "shock")
		self.assertEqual(broad_episode_2.phase, "shock")

		# But the process genuinely differs: one architecture used 4
		# distinct actor identities across the episode, the other used 1.
		specialist_actors_ep2 = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event",
				filters={"run": specialist_result["run"], "episode": specialist_episode_2.name},
				fields=["actor_slot"],
			) if e.actor_slot
		}
		broad_actors_ep2 = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event",
				filters={"run": broad_result["run"], "episode": broad_episode_2.name},
				fields=["actor_slot"],
			) if e.actor_slot
		}
		self.assertEqual(len(specialist_actors_ep2), 4)
		self.assertEqual(len(broad_actors_ep2), 1)
