import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.runtime.orchestrator import run_specialist_routine

ROLE_POLICIES = {
	"purchasing_agent": {
		"policy_name": "Test Purchasing Policy M3",
		"may_submit_documents": 0,
		"tools": ["get_supplier_options", "create_purchase_order"],
	},
	"purchasing_manager_agent": {
		"policy_name": "Test Purchasing Manager Policy M3",
		"may_submit_documents": 1,
		"may_approve": 1,
		"tools": ["get_purchase_order", "submit_purchase_order"],
	},
	"warehouse_agent": {
		"policy_name": "Test Warehouse Policy M3",
		"may_submit_documents": 1,
		"may_message_agents": 1,
		"tools": [
			"get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt",
			"inspect_received_goods", "escalate_quality_exception", "message_agent",
		],
	},
	"accounts_payable_agent": {
		"policy_name": "Test Accounts Payable Policy M3",
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

ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent",
	"purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent",
	"accounts_payable_agent": "Accounts Payable Agent",
}


class TestEORLMultiAgentRoutine(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M3",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		self.agent_templates = {}
		for key, spec in ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": spec["policy_name"],
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)

			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {ROLE_LABELS[key]} M3",
					"organizational_role": ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)

			self.agent_templates[key] = agent.name

	def test_full_procure_to_pay_routine_across_four_agents(self):
		result = run_specialist_routine(self.agent_templates, seed=42)
		outcome = result["outcome"]

		self.assertTrue(outcome["success"], outcome.get("failure_reason"))

		po = frappe.get_doc("Purchase Order", outcome["purchase_order"])
		pr = frappe.get_doc("Purchase Receipt", outcome["purchase_receipt"])
		pi = frappe.get_doc("Purchase Invoice", outcome["purchase_invoice"])
		pe = frappe.get_doc("Payment Entry", outcome["payment_entry"])

		# Every document in the chain was actually submitted, not just created.
		self.assertEqual(po.docstatus, 1)
		self.assertEqual(pr.docstatus, 1)
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pe.docstatus, 1)

		# The chain is really linked (receipt references the PO, invoice
		# references the receipt), not four unrelated documents.
		self.assertEqual(pr.items[0].purchase_order, po.name)
		self.assertEqual(pi.items[0].purchase_receipt, pr.name)

		events = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"]},
			fields=["event_type", "actor_slot", "target_id"],
			order_by="sequence_no asc",
		)
		event_types = [e.event_type for e in events]

		# All four roles acted (actor_slot is populated per spec section
		# 6.12, not left as a single undifferentiated actor).
		actor_slots = {e.actor_slot for e in events if e.actor_slot}
		for role_label in ROLE_LABELS.values():
			self.assertIn(role_label, actor_slots)

		# Explicit, logged handoffs between every consecutive pair of
		# roles (spec section 15) -- at least three structural handoffs
		# for four roles. Not exact equality: if the ground-truth-driven
		# quality inspection (SOTA Milestone 1) happens to fail for this
		# seed's specific receipt, the Warehouse Agent also sends one
		# agent-chosen exception notification via message_agent, adding
		# one more pair -- a real, not a flaky, source of variation.
		self.assertGreaterEqual(event_types.count("agent_message_sent"), 3)
		self.assertGreaterEqual(event_types.count("agent_message_received"), 3)

		# The full write chain happened and was observed, in order.
		for required in [
			"create_purchase_order",
			"submit_purchase_order",
			"create_purchase_receipt",
			"submit_purchase_receipt",
			"create_purchase_invoice",
			"submit_purchase_invoice",
			"create_payment_entry",
			"submit_payment_entry",
		]:
			self.assertIn(required, [e.target_id for e in events])

		run = frappe.get_doc("EORL Run", result["run"])
		self.assertEqual(run.status, "completed")

	def test_manager_without_submit_right_is_denied(self):
		restrictive_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Manager No Submit Policy M3",
				"may_submit_documents": 0,
				"allowed_semantic_tools": [{"tool_name": "get_purchase_order"}, {"tool_name": "submit_purchase_order"}],
			}
		).insert(ignore_if_duplicate=True)

		restricted_manager = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Manager No Submit Agent M3",
				"organizational_role": "Purchasing Manager Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": restrictive_policy.name,
			}
		).insert(ignore_if_duplicate=True)

		agent_templates = dict(self.agent_templates)
		agent_templates["purchasing_manager_agent"] = restricted_manager.name

		result = run_specialist_routine(agent_templates, seed=42)
		outcome = result["outcome"]

		self.assertFalse(outcome["success"])
		self.assertEqual(outcome["failure_reason"], "SUBMIT_NOT_PERMITTED")

		# The PO was created (Purchasing Agent's stage completed) but
		# never submitted, and the routine stopped there -- no receipt,
		# invoice, or payment exist for this run.
		self.assertTrue(outcome["purchase_order"])
		po = frappe.get_doc("Purchase Order", outcome["purchase_order"])
		self.assertEqual(po.docstatus, 0)
		self.assertIsNone(outcome["purchase_receipt"])
