import frappe
from frappe.tests.utils import FrappeTestCase

TEST_NAMES = {
	"model_profile": "Test Deterministic Profile",
	"memory_profile": "Test Memory Profile",
	"tool_policy": "Test Tool Policy",
	"agent_template": "Test Purchasing Agent",
}


class TestEORLAgentTemplate(FrappeTestCase):
	def tearDown(self):
		for doctype, name in [
			("EORL Agent Template", TEST_NAMES["agent_template"]),
			("EORL Tool Policy", TEST_NAMES["tool_policy"]),
			("EORL Memory Profile", TEST_NAMES["memory_profile"]),
			("EORL Model Profile", TEST_NAMES["model_profile"]),
		]:
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True)

	def test_agent_template_binds_profiles_and_policy(self):
		model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": TEST_NAMES["model_profile"],
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert()

		memory_profile = frappe.get_doc(
			{
				"doctype": "EORL Memory Profile",
				"profile_name": TEST_NAMES["memory_profile"],
				"local_memory_enabled": 1,
				"local_backend": "episodic",
			}
		).insert()

		tool_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": TEST_NAMES["tool_policy"],
				"may_submit_documents": 1,
				"allowed_semantic_tools": [
					{"tool_name": "get_pending_material_requests"},
					{"tool_name": "create_purchase_order"},
				],
			}
		).insert()

		agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": TEST_NAMES["agent_template"],
				"organizational_role": "Purchasing Agent",
				"model_profile": model_profile.name,
				"memory_profile": memory_profile.name,
				"tool_policy": tool_policy.name,
			}
		).insert()

		self.assertEqual(agent.model_profile, model_profile.name)
		self.assertEqual(agent.memory_profile, memory_profile.name)
		self.assertEqual(agent.tool_policy, tool_policy.name)

		reloaded_policy = frappe.get_doc("EORL Tool Policy", tool_policy.name)
		self.assertEqual(len(reloaded_policy.allowed_semantic_tools), 2)
		self.assertEqual(reloaded_policy.allowed_semantic_tools[1].tool_name, "create_purchase_order")
