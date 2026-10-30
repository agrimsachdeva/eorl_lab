import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import stats
from eorl_lab.api.analysis import compute_power_analysis, compute_replication_diagnostics, compute_required_sample_size, compute_robustness_jackknife
from eorl_lab.runtime.orchestrator import run_architecture

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry",
	"inspect_received_goods", "escalate_quality_exception", "message_agent",
]


class TestEORLPowerAnalysisStats(FrappeTestCase):
	"""Pure-function correctness for SOTA Milestone 8's power/replication/
	robustness additions -- no Frappe/run data needed."""

	def test_zero_effect_power_is_near_alpha(self):
		result = stats.simulate_power(0.0, n_per_group=20, alpha=0.05, n_simulations=3000, seed=1)
		self.assertAlmostEqual(result["power"], 0.05, delta=0.03)

	def test_large_effect_small_n_gives_high_power(self):
		result = stats.simulate_power(2.0, n_per_group=15, alpha=0.05, n_simulations=1500, seed=2)
		self.assertGreater(result["power"], 0.9)

	def test_moderate_effect_small_n_is_underpowered(self):
		result = stats.simulate_power(0.5, n_per_group=10, alpha=0.05, n_simulations=1500, seed=3)
		self.assertLess(result["power"], 0.5)

	def test_required_sample_size_finds_a_small_n_for_a_large_effect(self):
		result = stats.required_sample_size(1.5, target_power=0.8, alpha=0.05, max_n=100, n_simulations=800, seed=4)
		self.assertIsNotNone(result["required_n_per_group"])
		self.assertGreaterEqual(result["achieved_power"], 0.8 - 0.1)  # simulation noise tolerance

	def test_required_sample_size_reports_not_reached_rather_than_guessing(self):
		# A tiny effect with a very low max_n ceiling should not be
		# reachable -- confirms the function reports failure honestly.
		result = stats.required_sample_size(0.05, target_power=0.95, alpha=0.05, max_n=5, n_simulations=300, seed=5)
		self.assertIsNone(result["required_n_per_group"])
		self.assertEqual(result["searched_up_to"], 5)

	def test_replication_stability_trajectory_length_and_shape(self):
		a = [5.1, 5.3, 4.9, 5.0, 5.2, 4.8]
		b = [4.0, 4.2, 3.9, 4.1, 4.0, 3.8]
		trajectory = stats.replication_stability(a, b)
		self.assertEqual(len(trajectory), 5)  # n=2..6
		self.assertEqual(trajectory[0]["n_per_group"], 2)
		self.assertEqual(trajectory[-1]["n_per_group"], 6)
		# The final point's mean_diff must equal a plain Welch test on the full data.
		full = stats.welch_t_test(a, b)
		self.assertAlmostEqual(trajectory[-1]["mean_diff"], full["mean_diff"])

	def test_jackknife_sensitivity_baseline_matches_full_welch_test(self):
		a = [5.1, 5.3, 4.9, 5.0, 5.2, 4.8]
		b = [4.0, 4.2, 3.9, 4.1, 4.0, 3.8]
		result = stats.jackknife_sensitivity(a, b)
		full = stats.welch_t_test(a, b)
		self.assertAlmostEqual(result["baseline"]["mean_diff"], full["mean_diff"])
		self.assertEqual(len(result["rows"]), 1 + len(a) + len(b))
		self.assertIsNone(result["rows"][0]["excluded"])

	def test_jackknife_sensitivity_requires_minimum_group_size(self):
		with self.assertRaises(ValueError):
			stats.jackknife_sensitivity([1, 2], [1, 2, 3])


class TestEORLPowerAndRobustnessAPI(FrappeTestCase):
	"""Frappe-integration tests: the whitelisted wrappers, and the
	robustness/replication diagnostics reading real run-level metric
	values the same way compare_groups does."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test M8 Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		self.broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy", "policy_name": "Test M8 Broad Policy",
				"may_submit_documents": 1, "may_approve": 1, "may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test M8 General Purchasing Agent",
				"organizational_role": "General Purchasing Agent", "model_profile": self.model_profile.name,
				"tool_policy": self.broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test M8 Broad Autonomy",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.runs_a = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (801, 802, 803, 804)]
		self.runs_b = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (811, 812, 813, 814)]
		self.plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test M8 Plan",
				"outcome_metric": "actor_continuity", "analysis_unit": "run",
			}
		).insert(ignore_if_duplicate=True)

	def test_compute_power_analysis_whitelisted_wrapper(self):
		result = compute_power_analysis(0.8, 15, alpha=0.05, n_simulations=500)
		self.assertIn("power", result)
		self.assertGreaterEqual(result["power"], 0.0)
		self.assertLessEqual(result["power"], 1.0)

	def test_compute_required_sample_size_whitelisted_wrapper(self):
		result = compute_required_sample_size(1.2, target_power=0.75, alpha=0.05, max_n=60)
		self.assertIn("required_n_per_group", result)

	def test_replication_diagnostics_reads_real_run_level_metric_values(self):
		result = compute_replication_diagnostics(self.plan.name, self.runs_a, self.runs_b)
		self.assertEqual(result["outcome_metric"], "actor_continuity")
		self.assertEqual(len(result["trajectory"]), 3)  # n=2,3,4
		self.assertEqual(result["trajectory"][0]["n_per_group"], 2)
		self.assertEqual(result["trajectory"][-1]["n_per_group"], 4)

	def test_robustness_jackknife_labels_name_the_actual_excluded_run(self):
		result = compute_robustness_jackknife(self.plan.name, self.runs_a, self.runs_b)
		self.assertEqual(len(result["rows"]), 1 + len(self.runs_a) + len(self.runs_b))
		self.assertEqual(result["rows"][0]["label"], "Full sample")
		excluded_labels = {row["label"] for row in result["rows"][1:]}
		for run_name in self.runs_a + self.runs_b:
			self.assertIn(f"Excl. {run_name}", excluded_labels)
