import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import stats
from eorl_lab.api.analysis import compare_groups, export_results_table
from eorl_lab.runtime.orchestrator import run_architecture

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry",
	"inspect_received_goods", "escalate_quality_exception", "message_agent",
]


class TestEORLStatsEnginePhase2(FrappeTestCase):
	"""Pure-function correctness checks for SOTA Milestone 6's additions
	-- no Frappe/run data needed."""

	def test_tost_establishes_equivalence_with_generous_bounds(self):
		a = [1.00, 1.01, 0.99, 1.02, 0.98]
		b = [1.00, 1.00, 1.01, 0.99, 1.00]
		result = stats.tost_equivalence(a, b, -0.5, 0.5)
		self.assertTrue(result["equivalent"])
		self.assertLess(result["p_value"], 0.05)

	def test_tost_fails_to_establish_equivalence_with_narrow_bounds(self):
		a = [1.00, 1.01, 0.99, 1.02, 0.98]
		b = [1.00, 1.00, 1.01, 0.99, 1.00]
		result = stats.tost_equivalence(a, b, -0.001, 0.001)
		self.assertFalse(result["equivalent"])

	def test_tost_rejects_inverted_bounds(self):
		with self.assertRaises(ValueError):
			stats.tost_equivalence([1, 2, 3], [1, 2, 3], 1.0, -1.0)

	def test_mixed_effects_recovers_known_fixed_effect(self):
		# Small cluster-level noise relative to a clear 2.0 shift --
		# the model should recover it closely and report significance.
		import random
		rng = random.Random(0)
		episode_values_a, run_ids_a = [], []
		for run_idx in range(6):
			intercept = rng.gauss(0, 0.1)
			for _ in range(10):
				episode_values_a.append(5.0 + intercept + rng.gauss(0, 0.2))
				run_ids_a.append(f"runA{run_idx}")
		episode_values_b, run_ids_b = [], []
		for run_idx in range(6):
			intercept = rng.gauss(0, 0.1)
			for _ in range(10):
				episode_values_b.append(7.0 + intercept + rng.gauss(0, 0.2))
				run_ids_b.append(f"runB{run_idx}")

		result = stats.mixed_effects_comparison(episode_values_a, run_ids_a, episode_values_b, run_ids_b)
		self.assertAlmostEqual(result["coefficient"], 2.0, delta=0.3)
		self.assertLess(result["p_value"], 0.01)
		self.assertEqual(result["n_episodes_a"], 60)
		self.assertEqual(result["n_clusters_a"], 6)
		self.assertTrue(result["converged"])

	def test_mixed_effects_rejects_mismatched_lengths(self):
		with self.assertRaises(ValueError):
			stats.mixed_effects_comparison([1.0, 2.0], ["r1"], [1.0], ["r1", "r2"])

	def test_mixed_effects_requires_at_least_two_clusters_per_group(self):
		with self.assertRaises(ValueError):
			stats.mixed_effects_comparison([1.0, 2.0], ["r1", "r1"], [3.0, 4.0], ["r2", "r3"])


class TestEORLComparisonEnginePhase2(FrappeTestCase):
	"""SOTA Milestone 6: equivalence testing, mixed-effects episode-level
	analysis, and publication table export wired through compare_groups."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test Analysis2 Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		self.broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy", "policy_name": "Test Analysis2 Broad Policy",
				"may_submit_documents": 1, "may_approve": 1, "may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Analysis2 General Purchasing Agent",
				"organizational_role": "General Purchasing Agent", "model_profile": self.model_profile.name,
				"tool_policy": self.broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test Analysis2 Broad Autonomy",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.runs_a = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (501, 502, 503)]
		self.runs_b = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (601, 602, 603)]

	def test_equivalence_bounds_add_a_tost_result(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Equivalence Plan",
				"outcome_metric": "success_rate", "analysis_unit": "run",
				"equivalence_bounds": "-0.5,0.5", "permutation_iterations": 500,
			}
		).insert(ignore_if_duplicate=True)
		result = compare_groups(plan.name, self.runs_a, self.runs_b)
		test_families = {r["test"] for r in result["results"]}
		self.assertIn("tost_equivalence", test_families)
		self.assertEqual(len(result["analysis_result_names"]), 3)  # welch + permutation + tost

	def test_malformed_equivalence_bounds_is_rejected(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Bad Equivalence Plan",
				"outcome_metric": "success_rate", "analysis_unit": "run",
				"equivalence_bounds": "not-a-range", "permutation_iterations": 500,
			}
		).insert(ignore_if_duplicate=True)
		with self.assertRaises(frappe.ValidationError):
			compare_groups(plan.name, self.runs_a, self.runs_b)

	def test_episode_level_without_mixed_effects_model_family_is_still_blocked(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Episode No Model",
				"outcome_metric": "success_rate", "analysis_unit": "episode",
			}
		).insert(ignore_if_duplicate=True)
		with self.assertRaises(frappe.ValidationError):
			compare_groups(plan.name, self.runs_a, self.runs_b)

	def test_episode_level_with_mixed_effects_succeeds(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Episode Mixed Effects",
				"outcome_metric": "success_rate", "analysis_unit": "episode", "model_family": "mixed_effects",
			}
		).insert(ignore_if_duplicate=True)
		result = compare_groups(plan.name, self.runs_a, self.runs_b)
		self.assertEqual(result["n_independent_runs_a"], 3)  # distinct run clusters, not episodes
		self.assertEqual(result["n_episodes_a"], 6)  # 3 runs x 2 episodes
		self.assertEqual(len(result["analysis_result_names"]), 1)
		self.assertEqual(result["results"][0]["test"], "mixed_effects")

		doc = frappe.get_doc("EORL Analysis Result", result["analysis_result_names"][0])
		self.assertEqual(doc.test_family, "mixed_effects")
		self.assertEqual(doc.n_independent_runs_a, 3)
		self.assertEqual(doc.n_episodes_a, 6)

	def test_episode_level_rejects_a_metric_with_no_episode_definition(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Episode Bad Metric",
				"outcome_metric": "sequence_entropy", "analysis_unit": "episode", "model_family": "mixed_effects",
			}
		).insert(ignore_if_duplicate=True)
		with self.assertRaises(frappe.ValidationError):
			compare_groups(plan.name, self.runs_a, self.runs_b)

	def test_export_results_table_markdown_and_csv(self):
		plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis2 Export Plan",
				"outcome_metric": "success_rate", "analysis_unit": "run", "permutation_iterations": 500,
			}
		).insert(ignore_if_duplicate=True)
		compare_groups(plan.name, self.runs_a, self.runs_b)

		markdown = export_results_table(plan.name, fmt="markdown")
		self.assertIn("test_family", markdown)
		self.assertIn("welch_t", markdown)
		self.assertIn("|", markdown)

		csv_text = export_results_table(plan.name, fmt="csv")
		self.assertIn("test_family", csv_text)
		self.assertIn("welch_t", csv_text)
		self.assertNotIn("|", csv_text)
