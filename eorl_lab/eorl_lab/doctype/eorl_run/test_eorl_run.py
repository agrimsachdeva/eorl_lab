import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.runtime.orchestrator import run_demo_episode


class TestEORLRunVerticalSlice(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M2",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		self.tool_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Procurement Policy M2",
				"may_submit_documents": 0,
				"max_write_actions_per_episode": 1,
				"allowed_semantic_tools": [
					{"tool_name": "get_supplier_options"},
					{"tool_name": "create_purchase_order"},
				],
			}
		).insert(ignore_if_duplicate=True)

		self.agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Purchasing Agent M2",
				"organizational_role": "Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": self.tool_policy.name,
				"initial_system_instructions": "You are the purchasing agent for the procure-to-pay routine.",
			}
		).insert(ignore_if_duplicate=True)

	def test_vertical_slice_creates_real_purchase_order_with_full_trace(self):
		result = run_demo_episode(self.agent.name, seed=42)

		self.assertTrue(result["outcome"]["success"])
		po_name = result["outcome"]["purchase_order"]
		self.assertTrue(frappe.db.exists("Purchase Order", po_name))

		po = frappe.get_doc("Purchase Order", po_name)
		self.assertEqual(po.docstatus, 0)  # created but not submitted (policy denies submit)

		events = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"]},
			fields=["event_type", "sequence_no"],
			order_by="sequence_no asc",
		)
		event_types = [e.event_type for e in events]

		for required in [
			"run_initialized",
			"episode_initialized",
			"environment_observed",
			"tool_requested",
			"tool_authorized",
			"tool_result",
			"erp_mutation",
			"episode_outcome",
			"run_completed",
		]:
			self.assertIn(required, event_types)

		run = frappe.get_doc("EORL Run", result["run"])
		self.assertEqual(run.status, "completed")
		self.assertEqual(run.event_count, len(events))

		episode = frappe.get_doc("EORL Episode", result["episode"])
		self.assertEqual(episode.status, "completed")
		self.assertTrue(episode.success)

	def test_authority_denies_tool_outside_policy(self):
		restrictive_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Read Only Policy M2",
				"allowed_semantic_tools": [{"tool_name": "get_supplier_options"}],
			}
		).insert(ignore_if_duplicate=True)

		restricted_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Restricted Agent M2",
				"organizational_role": "Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": restrictive_policy.name,
			}
		).insert(ignore_if_duplicate=True)

		result = run_demo_episode(restricted_agent.name, seed=42)

		self.assertFalse(result["outcome"]["success"])
		self.assertEqual(result["outcome"]["failure_reason"], "TOOL_NOT_IN_POLICY")

		events = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"]},
			fields=["event_type"],
			order_by="sequence_no asc",
			pluck="event_type",
		)
		self.assertIn("tool_denied", events)
		self.assertNotIn("erp_mutation", events)
