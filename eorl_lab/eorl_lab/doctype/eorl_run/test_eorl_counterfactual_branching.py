import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.runtime.orchestrator import branch_run, get_full_branch_history, run_architecture

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
	"inspect_received_goods",
	"escalate_quality_exception",
	"message_agent",
]

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {
		"tools": ["get_supplier_options", "create_purchase_order"],
	},
	"purchasing_manager_agent": {
		"may_submit_documents": 1,
		"may_approve": 1,
		"tools": ["get_purchase_order", "submit_purchase_order"],
	},
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


class TestEORLCounterfactualBranching(FrappeTestCase):
	"""SOTA Milestone 2 (V2 spec section 17): clone a run's state at
	episode t and branch into diverging conditions that share identical
	history up to that point."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M2Branch",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		self.memory_profile = frappe.get_doc(
			{
				"doctype": "EORL Memory Profile",
				"profile_name": "Test Recent Memory Profile M2Branch",
				"local_memory_enabled": 1,
				"local_backend": "recent",
				"local_top_k": 3,
			}
		).insert(ignore_if_duplicate=True)

		broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Broad Autonomy Policy M2Branch",
				"may_submit_documents": 1,
				"may_approve": 1,
				"may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test General Purchasing Agent M2Branch",
				"organizational_role": "General Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": broad_policy.name,
				"memory_profile": self.memory_profile.name,
			}
		).insert(ignore_if_duplicate=True)
		self.broad_autonomy_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Broad Autonomy M2Branch",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy M2Branch",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} M2Branch",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})
		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff M2Branch",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

	def _episode_names(self, run_name, upto=None):
		filters = {"run": run_name}
		episodes = frappe.get_all(
			"EORL Episode", filters=filters, fields=["name", "episode_number"], order_by="episode_number asc"
		)
		if upto is not None:
			episodes = [e for e in episodes if e.episode_number <= upto]
		return episodes

	def test_branch_run_shares_identical_history_through_branch_point_then_diverges(self):
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=71, episode_count=2)
		self.assertTrue(parent["outcome"]["success"], parent["outcome"].get("failure_reason"))

		branch_a = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.broad_autonomy_architecture.name,
			intervention_description="continues broad_autonomy unchanged",
		)
		branch_b = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.specialist_architecture.name,
			intervention_description="switches to specialist_handoff after episode 2",
		)
		self.assertTrue(branch_a["outcome"]["success"], branch_a["outcome"].get("failure_reason"))
		self.assertTrue(branch_b["outcome"]["success"], branch_b["outcome"].get("failure_reason"))
		self.assertNotEqual(branch_a["branch_run"], branch_b["branch_run"])

		history_a = get_full_branch_history(branch_a["branch_run"])
		history_b = get_full_branch_history(branch_b["branch_run"])

		# Spec section 17/31.5's acceptance test: identical history
		# through the branch point.
		self.assertEqual(len(history_a), 3)
		self.assertEqual(len(history_b), 3)
		for i in range(2):
			self.assertEqual(history_a[i].run, parent["run"])
			self.assertEqual(history_b[i].run, parent["run"])
			self.assertEqual(history_a[i].name, history_b[i].name)
			self.assertEqual(history_a[i].episode_number, history_b[i].episode_number)
			self.assertEqual(history_a[i].scenario_case_id, history_b[i].scenario_case_id)
			self.assertEqual(history_a[i].phase, history_b[i].phase)

		# ...then genuinely diverges after the branch point: each child
		# owns its own, distinct episode 3 (never a shared/duplicated
		# record), and the underlying process structurally differs.
		self.assertEqual(history_a[2].run, branch_a["branch_run"])
		self.assertEqual(history_b[2].run, branch_b["branch_run"])
		self.assertNotEqual(history_a[2].name, history_b[2].name)

		actors_a = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event", filters={"run": branch_a["branch_run"], "episode": history_a[2].name},
				fields=["actor_slot"],
			) if e.actor_slot
		}
		actors_b = {
			e.actor_slot for e in frappe.get_all(
				"EORL Event", filters={"run": branch_b["branch_run"], "episode": history_b[2].name},
				fields=["actor_slot"],
			) if e.actor_slot
		}
		self.assertEqual(len(actors_a), 1)
		self.assertEqual(len(actors_b), 4)

	def test_branch_run_requires_source_run_to_have_reached_branch_episode(self):
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=72, episode_count=1)
		self.assertTrue(parent["outcome"]["success"])
		with self.assertRaises(frappe.ValidationError):
			branch_run(parent["run"], branch_episode=5, additional_episode_count=1)

	def test_get_full_branch_history_on_unbranched_run_returns_only_its_own_episodes(self):
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=73, episode_count=2)
		history = get_full_branch_history(parent["run"])
		self.assertEqual(len(history), 2)
		self.assertTrue(all(ep.run == parent["run"] for ep in history))

	def test_branch_clones_actor_memory_accumulated_through_the_branch_point(self):
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=74, episode_count=2)
		self.assertTrue(parent["outcome"]["success"])

		pre_branch_episodes = self._episode_names(parent["run"], upto=2)
		source_memory_count = frappe.db.count(
			"EORL Memory Record",
			{"run": parent["run"], "episode": ["in", [e.name for e in pre_branch_episodes]]},
		)
		self.assertGreater(source_memory_count, 0, "fixture should actually produce memory records to clone")

		branch = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.broad_autonomy_architecture.name,
		)
		self.assertEqual(branch["cloned_memory_count"], source_memory_count)

		cloned_count = frappe.db.count("EORL Memory Record", {"run": branch["branch_run"]})
		# Cloned (pre-branch) records plus whatever the one post-branch
		# episode itself newly wrote.
		self.assertGreaterEqual(cloned_count, source_memory_count)

		cloned_records = frappe.get_all(
			"EORL Memory Record",
			filters={"run": branch["branch_run"], "episode": ["in", [e.name for e in pre_branch_episodes]]},
			fields=["episode", "actor", "action", "success"],
			order_by="episode asc, action asc",
		)
		source_records = frappe.get_all(
			"EORL Memory Record",
			filters={"run": parent["run"], "episode": ["in", [e.name for e in pre_branch_episodes]]},
			fields=["episode", "actor", "action", "success"],
			order_by="episode asc, action asc",
		)
		self.assertEqual(len(cloned_records), len(source_records))
		self.assertEqual(
			sorted((r.episode, r.actor, r.action, r.success) for r in cloned_records),
			sorted((r.episode, r.actor, r.action, r.success) for r in source_records),
		)

	def test_branch_lineage_fields_are_recorded_and_branch_record_created(self):
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=75, episode_count=2)
		branch = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.broad_autonomy_architecture.name,
			intervention_description="test intervention",
		)

		child = frappe.get_doc("EORL Run", branch["branch_run"])
		self.assertEqual(child.parent_run, parent["run"])
		self.assertEqual(child.branch_point_episode, 2)

		branch_records = frappe.get_all(
			"EORL Branch",
			filters={"parent_run": parent["run"], "child_run": branch["branch_run"]},
			fields=["source_episode", "intervention_description"],
		)
		self.assertEqual(len(branch_records), 1)
		self.assertEqual(branch_records[0].source_episode, 2)
		self.assertEqual(branch_records[0].intervention_description, "test intervention")

		# run_branched event actually emitted, not just the DocType row.
		branched_events = frappe.get_all(
			"EORL Event", filters={"run": branch["branch_run"], "event_type": "run_branched"}, fields=["name"]
		)
		self.assertEqual(len(branched_events), 1)

	def test_branches_share_erp_master_data_but_each_creates_its_own_documents(self):
		"""Honest-scope caveat (see orchestrator.branch_run docstring and
		SOTA_ROADMAP.md): ERP state is NOT forked per branch -- both
		children mutate the SAME underlying company ledger. What IS
		isolated is each branch's own transactional documents: a branch
		never reuses or duplicates another branch's Purchase Order."""
		parent = run_architecture(self.broad_autonomy_architecture.name, seed=76, episode_count=1)
		branch_a = branch_run(parent["run"], branch_episode=1, additional_episode_count=1,
			architecture_name=self.broad_autonomy_architecture.name)
		branch_b = branch_run(parent["run"], branch_episode=1, additional_episode_count=1,
			architecture_name=self.broad_autonomy_architecture.name)

		po_a = frappe.get_doc("Purchase Order", branch_a["episodes"][0]["purchase_order"])
		po_b = frappe.get_doc("Purchase Order", branch_b["episodes"][0]["purchase_order"])

		self.assertNotEqual(po_a.name, po_b.name)  # independent transactional documents
		self.assertEqual(po_a.company, po_b.company)  # same shared company -- no ERP-state fork
