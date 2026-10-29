import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.api import experiments as experiments_api
from eorl_lab.api import exports as exports_api
from eorl_lab.api import metrics as metrics_api
from eorl_lab.api import traces as traces_api

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

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry",
	"inspect_received_goods", "escalate_quality_exception", "message_agent",
]


class TestEORLExperimentStudioAPIs(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M6",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy M6",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} M6",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})

		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff M6",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

		broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Broad Autonomy Policy M6",
				"may_submit_documents": 1,
				"may_approve": 1,
				"may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test General Purchasing Agent M6",
				"organizational_role": "General Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.broad_autonomy_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Broad Autonomy M6",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.experiment = frappe.get_doc(
			{
				"doctype": "EORL Experiment",
				"experiment_name": "Test Adaptive Repertoire Pilot M6",
				"research_question": "Does broader autonomy change routine coherence vs variety?",
				"architecture_a": self.specialist_architecture.name,
				"architecture_b": self.broad_autonomy_architecture.name,
				"episode_count": 2,
				"repetitions_per_cell": 1,
				"seed_strategy": "paired",
				"base_seed": 500,
			}
		).insert(ignore_if_duplicate=True)

	def test_cell_and_run_count(self):
		self.assertEqual(self.experiment.cell_count(), 2)
		self.assertEqual(self.experiment.total_run_count(), 2)

		summary = experiments_api.get_experiment_summary(self.experiment.name)
		self.assertEqual(summary["cell_count"], 2)
		self.assertEqual(summary["total_run_count"], 2)

	def test_validate_experiment(self):
		result = experiments_api.validate_experiment(self.experiment.name)
		self.assertTrue(result["valid"], result["errors"])
		self.assertEqual(result["total_run_count"], 2)

		# Simulates a realistic edge case Frappe's own Link validation
		# doesn't prevent: a regime_shift that existed when the
		# experiment was saved, then got deleted later. ignore_links is
		# needed here only to construct that already-stale state in the
		# test; validate_experiment's own check is what's under test.
		broken = frappe.get_doc(
			{
				"doctype": "EORL Experiment",
				"experiment_name": "Test Broken Experiment M6",
				"architecture_a": self.specialist_architecture.name,
				"regime_shift": "Does Not Exist M6",
			}
		)
		broken.insert(ignore_if_duplicate=True, ignore_links=True)
		result = experiments_api.validate_experiment(broken.name)
		self.assertFalse(result["valid"])
		self.assertTrue(any("regime_shift" in e for e in result["errors"]))

	def test_launch_pilot_runs_both_architectures_with_paired_seeds(self):
		result = experiments_api.launch_pilot(self.experiment.name)

		self.assertEqual(len(result["runs"]), 2)
		for run_info in result["runs"]:
			self.assertTrue(run_info["success"], run_info)
			self.assertEqual(run_info["seed"], self.experiment.base_seed)  # paired: rep 0 -> base_seed for both

		self.experiment.reload()
		self.assertEqual(self.experiment.status, "pilot_launched")

		run_names = [r["run"] for r in result["runs"]]

		# Trace Explorer's API over one of the launched runs.
		episodes = traces_api.list_episodes(run_names[0])
		self.assertEqual(len(episodes), 2)
		trace = traces_api.get_episode_trace(episodes[0]["name"])
		self.assertGreater(len(trace["events"]), 0)
		self.assertEqual(trace["events"][0]["sequence_no"], min(e["sequence_no"] for e in trace["events"]))

		# Compare Runs' API over both launched runs: different actor
		# cardinality (4 vs 1), same episode count.
		comparison = metrics_api.compare_runs(run_names)
		self.assertEqual(len(comparison), 2)
		distinct_actor_counts = sorted(c["distinct_actor_count"] for c in comparison)
		self.assertEqual(distinct_actor_counts, [1, 4])
		for c in comparison:
			self.assertEqual(c["episode_count"], 2)
			self.assertEqual(c["success_rate"], 1.0)

		# Export bundle's API over one run.
		bundle = exports_api.export_run_bundle(run_names[0])
		self.assertEqual(len(bundle["episodes"]), 2)
		self.assertGreater(len(bundle["events"]), 0)
		self.assertEqual(bundle["run_manifest"]["name"], run_names[0])
