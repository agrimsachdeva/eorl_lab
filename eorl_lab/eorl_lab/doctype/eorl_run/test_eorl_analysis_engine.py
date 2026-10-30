import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import stats
from eorl_lab.api.analysis import compare_groups
from eorl_lab.runtime.orchestrator import branch_run, run_architecture

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry",
	"inspect_received_goods", "escalate_quality_exception", "message_agent",
]


class TestEORLStatsEngine(FrappeTestCase):
	"""Pure-function correctness checks against known reference values
	-- no Frappe/run data needed. scipy does the actual numerics; these
	assert this module wires it up correctly, not that scipy itself
	is correct."""

	def test_welch_t_matches_known_textbook_example(self):
		# The classic unequal-variance Behrens-Fisher textbook example
		# (also reproduced by R's t.test(a, b) and scipy directly):
		# t ~= 1.959, df ~= 7.03, p ~= 0.0908.
		a = [30.02, 29.99, 30.11, 29.97, 30.01, 29.99]
		b = [29.89, 29.93, 29.72, 29.98, 30.02, 29.98]
		result = stats.welch_t_test(a, b)
		self.assertAlmostEqual(result["t_statistic"], 1.959, places=2)
		self.assertAlmostEqual(result["df"], 7.03, places=1)
		self.assertAlmostEqual(result["p_value"], 0.0908, places=3)

	def test_welch_t_identical_samples_gives_zero_diff_and_p_one(self):
		a = [1.0, 2.0, 3.0, 4.0, 5.0]
		result = stats.welch_t_test(a, list(a))  # list(a): identical values, distinct list object
		self.assertAlmostEqual(result["mean_diff"], 0.0)
		self.assertAlmostEqual(result["p_value"], 1.0)

	def test_welch_t_raises_below_minimum_group_size(self):
		with self.assertRaises(ValueError):
			stats.welch_t_test([1.0], [1.0, 2.0])

	def test_permutation_test_matches_exact_enumeration(self):
		# Same dataset as the Welch example above. Exhaustive enumeration
		# over all C(12,6)=924 relabelings (using the same float
		# arithmetic as the implementation) gives exactly 52/924 =
		# 0.05628 -- verified independently by brute force outside this
		# test. A large n_iterations Monte Carlo run should land close.
		a = [30.02, 29.99, 30.11, 29.97, 30.01, 29.99]
		b = [29.89, 29.93, 29.72, 29.98, 30.02, 29.98]
		result = stats.permutation_test(a, b, n_iterations=20000, seed=1)
		self.assertAlmostEqual(result["p_value"], 0.0563, delta=0.015)

	def test_hedges_g_sign_and_zero_case(self):
		self.assertGreater(stats.hedges_g([5, 6, 7], [1, 2, 3]), 0)
		self.assertLess(stats.hedges_g([1, 2, 3], [5, 6, 7]), 0)
		self.assertEqual(stats.hedges_g([1, 1, 1], [1, 1, 1]), 0.0)

	def test_paired_t_test_requires_equal_length(self):
		with self.assertRaises(ValueError):
			stats.paired_t_test([1.0, 2.0], [1.0, 2.0, 3.0])

	def test_paired_t_and_independent_t_can_disagree_on_the_same_data(self):
		# The whole point of pairing: correlated pairs can show a
		# reliable within-pair effect that an independent-groups test,
		# ignorant of the correlation, would report as noisier/weaker.
		a = [10.0, 20.0, 30.0, 40.0, 50.0]
		b = [x - 1.0 for x in a]  # perfectly correlated, constant offset
		paired = stats.paired_t_test(a, b)
		independent = stats.welch_t_test(a, b)
		self.assertLess(paired["p_value"], independent["p_value"])


class TestEORLAnalysisPlanGuardrails(FrappeTestCase):
	"""SOTA Milestone 5 (V2 section 44): compare_groups enforces the
	independence guardrail and the paired-branch verification, rather
	than trusting the caller."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test Analysis Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		self.broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy", "policy_name": "Test Analysis Broad Policy",
				"may_submit_documents": 1, "may_approve": 1, "may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Analysis General Purchasing Agent",
				"organizational_role": "General Purchasing Agent", "model_profile": self.model_profile.name,
				"tool_policy": self.broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test Analysis Broad Autonomy",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.runs_a = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (201, 202, 203)]
		self.runs_b = [run_architecture(self.architecture.name, seed=s, episode_count=2)["run"] for s in (301, 302, 303)]

		self.plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis Plan Run Level",
				"outcome_metric": "success_rate", "analysis_unit": "run",
				"permutation_iterations": 500,
			}
		).insert(ignore_if_duplicate=True)

	def test_episode_level_analysis_unit_is_blocked(self):
		episode_plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis Plan Episode Level",
				"outcome_metric": "success_rate", "analysis_unit": "episode",
			}
		).insert(ignore_if_duplicate=True)
		with self.assertRaises(frappe.ValidationError):
			compare_groups(episode_plan.name, self.runs_a, self.runs_b)

	def test_run_level_comparison_succeeds_and_reports_both_tests(self):
		result = compare_groups(self.plan.name, self.runs_a, self.runs_b)
		self.assertEqual(result["n_independent_runs_a"], 3)
		self.assertEqual(result["n_independent_runs_b"], 3)
		self.assertEqual(result["n_episodes_a"], 6)  # 3 runs x 2 episodes
		self.assertFalse(result["paired"])

		test_families = {r["test"] for r in result["results"]}
		self.assertEqual(test_families, {"welch_t", "permutation"})
		self.assertEqual(len(result["analysis_result_names"]), 2)

	def test_analysis_results_carry_full_provenance(self):
		result = compare_groups(self.plan.name, self.runs_a, self.runs_b)
		for name in result["analysis_result_names"]:
			doc = frappe.get_doc("EORL Analysis Result", name)
			self.assertEqual(sorted(doc.run_ids_group_a.split(",")), sorted(self.runs_a))
			self.assertEqual(sorted(doc.run_ids_group_b.split(",")), sorted(self.runs_b))
			self.assertEqual(doc.n_independent_runs_a, 3)
			self.assertEqual(doc.n_episodes_a, 6)
			self.assertTrue(doc.stats_package_version.startswith("scipy"))
			# p_value legitimately lands as NULL (not a crash, not a
			# fabricated number) when success_rate has zero variance in
			# BOTH groups -- every run in this fixture succeeds every
			# episode, so this is the expected degenerate case here; the
			# mean/effect fields still carry real information regardless.
			self.assertTrue(doc.p_value is None or isinstance(doc.p_value, float))
			self.assertEqual(doc.mean_a, 1.0)
			self.assertEqual(doc.mean_b, 1.0)

	def test_fewer_than_two_runs_per_group_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			compare_groups(self.plan.name, [self.runs_a[0]], self.runs_b)

	def test_unpaired_groups_falsely_claiming_paired_by_are_rejected(self):
		paired_plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis Plan False Paired",
				"outcome_metric": "success_rate", "analysis_unit": "run", "paired_by": "branch_point",
			}
		).insert(ignore_if_duplicate=True)
		# self.runs_a and self.runs_b are NOT branches of each other at all.
		with self.assertRaises(frappe.ValidationError):
			compare_groups(paired_plan.name, self.runs_a, self.runs_b)

	def test_genuine_sibling_branch_pairs_are_accepted_and_use_paired_tests(self):
		parent = run_architecture(self.architecture.name, seed=400, episode_count=2)["run"]
		branch_1 = branch_run(parent, branch_episode=2, additional_episode_count=1, architecture_name=self.architecture.name)
		branch_2 = branch_run(parent, branch_episode=2, additional_episode_count=1, architecture_name=self.architecture.name)
		# second pair: another independent parent/branch-pair at the same episode, so N=2 pairs.
		parent_2 = run_architecture(self.architecture.name, seed=410, episode_count=2)["run"]
		branch_3 = branch_run(parent_2, branch_episode=2, additional_episode_count=1, architecture_name=self.architecture.name)
		branch_4 = branch_run(parent_2, branch_episode=2, additional_episode_count=1, architecture_name=self.architecture.name)

		paired_plan = frappe.get_doc(
			{
				"doctype": "EORL Analysis Plan", "plan_name": "Test Analysis Plan Genuine Paired",
				"outcome_metric": "success_rate", "analysis_unit": "run", "paired_by": "branch_point",
				"permutation_iterations": 500,
			}
		).insert(ignore_if_duplicate=True)

		result = compare_groups(
			paired_plan.name,
			[branch_1["branch_run"], branch_3["branch_run"]],
			[branch_2["branch_run"], branch_4["branch_run"]],
		)
		self.assertTrue(result["paired"])
		test_families = {r["test"] for r in result["results"]}
		self.assertEqual(test_families, {"paired_t", "paired_permutation"})
		for doc_name in result["analysis_result_names"]:
			self.assertEqual(frappe.db.get_value("EORL Analysis Result", doc_name, "paired"), 1)
