import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.api.metrics import compute_run_metrics
from eorl_lab.runtime.orchestrator import run_architecture

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {
		"may_submit_documents": 0,
		"tools": ["get_supplier_options", "create_purchase_order"],
	},
	"purchasing_manager_agent": {
		"may_submit_documents": 1,
		"tools": ["get_purchase_order", "submit_purchase_order"],
	},
	"warehouse_agent": {
		"may_submit_documents": 1,
		"tools": ["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt"],
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
BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry",
]


class TestProcessMetricsIntegration(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M7",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy M7",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} M7",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})

		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff M7",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

		broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Broad Autonomy Policy M7",
				"may_submit_documents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test General Purchasing Agent M7",
				"organizational_role": "General Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.broad_autonomy_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Broad Autonomy M7",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift",
				"shift_name": "Test Demand Shock M7",
				"trigger_episode": 2,
				"parameter_delta_json": frappe.as_json({"qty_multiplier": 1.8}),
			}
		).insert(ignore_if_duplicate=True)

	def test_specialist_and_broad_autonomy_metrics_discriminate_on_coherence_not_variety(self):
		"""The empirically-grounded claim this milestone makes: today's
		deterministic policies discriminate architectures on COHERENCE
		(actor identity / handoff structure) but NOT on routine VARIETY
		(every episode within a run follows the identical tool-call
		sequence -- see PROGRESS.md's documented finding). Both facts
		are asserted here, not just the flattering one."""
		specialist_result = run_architecture(self.specialist_architecture.name, seed=1, episode_count=3)
		broad_result = run_architecture(self.broad_autonomy_architecture.name, seed=1, episode_count=3)
		self.assertTrue(specialist_result["outcome"]["success"])
		self.assertTrue(broad_result["outcome"]["success"])

		specialist_metrics = compute_run_metrics(specialist_result["run"])["metrics"]
		broad_metrics = compute_run_metrics(broad_result["run"])["metrics"]

		# Variety: vacuous on both, honestly, because the policy never
		# branches on anything -- same path every episode.
		self.assertEqual(specialist_metrics["unique_sequence_count"], 1)
		self.assertEqual(broad_metrics["unique_sequence_count"], 1)
		self.assertEqual(specialist_metrics["sequence_entropy"], 0.0)
		self.assertEqual(broad_metrics["sequence_entropy"], 0.0)

		# Coherence: genuinely different, driven by organizational
		# structure, not by the policy varying what it does.
		self.assertEqual(broad_metrics["actor_switch_rate"], 0.0)
		self.assertGreater(specialist_metrics["actor_switch_rate"], broad_metrics["actor_switch_rate"])
		self.assertGreater(broad_metrics["actor_continuity"], specialist_metrics["actor_continuity"])
		self.assertGreater(broad_metrics["average_actor_run_length"], specialist_metrics["average_actor_run_length"])

		# Persisted, queryable, versioned -- not just returned in-memory.
		persisted = frappe.get_all(
			"EORL Metric",
			filters={"run": specialist_result["run"], "metric_name": "actor_switch_rate"},
			fields=["metric_value", "metric_version"],
		)
		self.assertEqual(len(persisted), 1)
		self.assertAlmostEqual(persisted[0].metric_value, specialist_metrics["actor_switch_rate"])
		self.assertEqual(persisted[0].metric_version, "v1")

	def test_full_pipeline_runs_end_to_end_with_a_real_regime_shift(self):
		"""Confirms the repertoire/adaptation branch of compute_run_metrics
		(only taken when a run actually has a shock phase) executes
		without error against a real orchestrator run, and persists
		versioned, viability-tagged metric rows -- even though their
		values are the honest vacuous ones on today's non-branching
		policy (see the test above)."""
		result = run_architecture(
			self.specialist_architecture.name, seed=2, episode_count=3, regime_shift=self.regime_shift.name
		)
		self.assertTrue(result["outcome"]["success"])

		metrics = compute_run_metrics(result["run"])["metrics"]
		for key in [
			"proportion_repertoire_reused_after_shock", "novel_viable_paths_after_shock",
			"path_extinction_rate", "immediate_post_shock_drop", "episodes_to_recover_90pct",
			"area_under_recovery_curve", "post_shock_error_rate",
		]:
			self.assertIn(key, metrics)

		# Nothing fails under this shock yet (it only changes quantity),
		# so performance never actually drops -- stated honestly, not
		# hidden, and asserted so a future change to the generator that
		# breaks this assumption is caught here.
		self.assertEqual(metrics["immediate_post_shock_drop"], 0.0)
		self.assertEqual(metrics["post_shock_error_rate"], 0.0)

		viability_tagged = frappe.get_all(
			"EORL Metric",
			filters={"run": result["run"], "metric_name": "path_extinction_rate"},
			fields=["metric_version"],
		)
		self.assertEqual(viability_tagged[0].metric_version, f"v1+viability:v1")
