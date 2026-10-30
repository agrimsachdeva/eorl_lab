import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.api.process import get_adaptation_view_data, get_network_explorer_data, get_process_explorer_data
from eorl_lab.runtime.orchestrator import run_architecture

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {"tools": ["get_supplier_options", "create_purchase_order"]},
	"purchasing_manager_agent": {"may_submit_documents": 1, "may_approve": 1, "tools": ["get_purchase_order", "submit_purchase_order"]},
	"warehouse_agent": {"may_submit_documents": 1, "may_message_agents": 1, "tools": [
		"get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt",
		"inspect_received_goods", "escalate_quality_exception", "message_agent",
	]},
	"accounts_payable_agent": {"may_submit_documents": 1, "tools": [
		"get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice",
		"create_payment_entry", "submit_payment_entry",
	]},
}
SPECIALIST_ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent", "purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent", "accounts_payable_agent": "Accounts Payable Agent",
}


class TestEORLProcessAndNetworkExplorer(FrappeTestCase):
	"""SOTA Milestone 7: the Process Explorer (DFG + swimlane) and
	Network Explorer backing APIs, plus the adaptation/event-study
	view's trajectory data."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test M7 Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy", "policy_name": f"Test M7 {key} Policy",
					"may_submit_documents": spec.get("may_submit_documents", 0), "may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template", "template_name": f"Test M7 {SPECIALIST_ROLE_LABELS[key]}",
					"organizational_role": SPECIALIST_ROLE_LABELS[key], "model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test M7 Specialist Handoff",
				"coordination_mode": "specialist_handoff", "actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift", "shift_name": "Test M7 Demand Shock",
				"trigger_episode": 3, "parameter_delta_json": frappe.as_json({"qty_multiplier": 1.5}),
			}
		).insert(ignore_if_duplicate=True)

		self.result = run_architecture(
			self.architecture.name, seed=701, episode_count=4, regime_shift=self.regime_shift.name
		)
		self.run = self.result["run"]

	def test_process_explorer_dfg_edges_cover_the_specialist_handoff_sequence(self):
		data = get_process_explorer_data(self.run)
		edge_pairs = {(e["from"], e["to"]) for e in data["dfg_edges"]}
		# directly_follows_graph is pooled over canonical process_path()
		# labels ("STAGE:tool_name"), not bare tool names -- the
		# specialist_handoff routine's real, structural stage order.
		self.assertIn(("PURCHASE_ORDER:create_purchase_order", "PURCHASE_ORDER:get_purchase_order"), edge_pairs)
		self.assertIn(("RECEIPT:inspect_received_goods", "RECEIPT:submit_purchase_receipt"), edge_pairs)
		for edge in data["dfg_edges"]:
			self.assertGreater(edge["count"], 0)
			self.assertGreaterEqual(edge["pct_of_from"], 0)
			self.assertLessEqual(edge["pct_of_from"], 100)

	def test_process_explorer_swimlane_has_one_row_per_episode_with_real_steps(self):
		data = get_process_explorer_data(self.run)
		self.assertEqual(len(data["swimlane"]), 4)
		for ep in data["swimlane"]:
			self.assertGreater(len(ep["steps"]), 0)
			for step in ep["steps"]:
				self.assertIn("actor_slot", step)
				self.assertIn("tool", step)
		# Specialist handoff uses 4 distinct actor slots across its steps.
		actors_used = {step["actor_slot"] for ep in data["swimlane"] for step in ep["steps"]}
		self.assertEqual(len(actors_used), 4)

	def test_network_explorer_returns_a_real_edge_from_the_quality_exception_path_or_empty(self):
		data = get_network_explorer_data(self.run)
		# message_agent only fires on a genuine quality exception (SOTA
		# Milestone 1); whether or not one occurred this seed, the shape
		# must always be valid.
		self.assertIsInstance(data["edges"], list)
		self.assertIsInstance(data["actors"], list)
		for edge in data["edges"]:
			self.assertIn(edge["from"], data["actors"])
			self.assertIn(edge["to"], data["actors"])
			self.assertGreater(edge["count"], 0)

	def test_adaptation_view_reports_the_regime_shift_trigger_episode(self):
		data = get_adaptation_view_data(self.run)
		self.assertEqual(data["regime_shift_trigger_episode"], 3)
		self.assertEqual(len(data["episodes"]), 4)
		phases = [e["phase"] for e in data["episodes"]]
		self.assertIn("shock", phases)

	def test_adaptation_view_reports_none_when_no_regime_shift_was_used(self):
		result = run_architecture(self.architecture.name, seed=702, episode_count=2)
		data = get_adaptation_view_data(result["run"])
		self.assertIsNone(data["regime_shift_trigger_episode"])
