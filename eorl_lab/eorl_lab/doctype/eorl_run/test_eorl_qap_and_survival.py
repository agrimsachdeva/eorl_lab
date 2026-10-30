import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import stats
from eorl_lab.api.analysis import compute_qap_comparison
from eorl_lab.api.process import get_survival_analysis_data
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


class TestEORLQAPAndSurvivalStats(FrappeTestCase):
	"""Pure-function correctness for SOTA Milestone 9's additions -- no
	Frappe/run data needed."""

	def test_qap_identical_networks_gives_perfect_correlation_and_minimum_reachable_p(self):
		net = {"A": {"B": 5, "C": 1}, "B": {"C": 3}, "C": {"D": 2}, "D": {"A": 1}}
		result = stats.qap_correlation(net, net, ["A", "B", "C", "D"], n_permutations=2000, seed=1)
		self.assertAlmostEqual(result["observed_correlation"], 1.0, places=6)
		# With 4 actors there are only 4! = 24 possible relabelings --
		# the smallest reachable p-value is 1/24.
		self.assertAlmostEqual(result["p_value"], 1 / 24, delta=0.02)

	def test_qap_unrelated_networks_are_not_significant(self):
		net_a = {"A": {"B": 5, "C": 1}, "B": {"C": 3}, "C": {"D": 2}, "D": {"A": 1}}
		net_b = {"A": {"D": 4}, "D": {"B": 2}, "B": {"A": 1}}
		result = stats.qap_correlation(net_a, net_b, ["A", "B", "C", "D"], n_permutations=2000, seed=2)
		self.assertGreater(result["p_value"], 0.05)

	def test_qap_requires_at_least_three_actors(self):
		with self.assertRaises(ValueError):
			stats.qap_correlation({}, {}, ["A", "B"])

	def test_kaplan_meier_survival_function_structure(self):
		result = stats.kaplan_meier_recovery([1, 2, 2, 3, 10, 10, 10, 10], [1, 1, 1, 1, 0, 0, 0, 0])
		self.assertEqual(result["n_events"], 4)
		self.assertEqual(result["n_censored"], 4)
		self.assertEqual(result["survival_function"][0]["survival_probability"], 1.0)
		# Survival should be non-increasing.
		probs = [p["survival_probability"] for p in result["survival_function"]]
		self.assertEqual(probs, sorted(probs, reverse=True))

	def test_kaplan_meier_all_recover_immediately_gives_low_median(self):
		result = stats.kaplan_meier_recovery([1, 1, 1, 1], [1, 1, 1, 1])
		self.assertEqual(result["median_recovery_time"], 1.0)

	def test_kaplan_meier_requires_matching_lengths(self):
		with self.assertRaises(ValueError):
			stats.kaplan_meier_recovery([1, 2], [1])


class TestEORLQAPAndSurvivalAPI(FrappeTestCase):
	"""Frappe-integration tests for the whitelisted QAP and survival
	analysis entrypoints against real runs."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test M9 Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy", "policy_name": f"Test M9 {key} Policy",
					"may_submit_documents": spec.get("may_submit_documents", 0), "may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template", "template_name": f"Test M9 {SPECIALIST_ROLE_LABELS[key]}",
					"organizational_role": SPECIALIST_ROLE_LABELS[key], "model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test M9 Specialist Handoff",
				"coordination_mode": "specialist_handoff", "actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)
		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift", "shift_name": "Test M9 Demand Shock",
				"trigger_episode": 2, "parameter_delta_json": frappe.as_json({"qty_multiplier": 1.5}),
			}
		).insert(ignore_if_duplicate=True)

	def test_qap_comparison_between_two_real_runs(self):
		run_a = run_architecture(self.architecture.name, seed=1001, episode_count=3)["run"]
		run_b = run_architecture(self.architecture.name, seed=1002, episode_count=3)["run"]
		result = compute_qap_comparison(run_a, run_b, n_permutations=500)
		self.assertEqual(result["run_a"], run_a)
		self.assertEqual(result["run_b"], run_b)
		self.assertEqual(len(result["actors"]), 4)  # specialist_handoff's 4 roles
		self.assertIsNotNone(result["p_value"])

	def test_survival_analysis_on_real_runs_with_a_regime_shift(self):
		runs = [
			run_architecture(self.architecture.name, seed=1100 + i, episode_count=4, regime_shift=self.regime_shift.name)["run"]
			for i in range(3)
		]
		result = get_survival_analysis_data(runs)
		self.assertEqual(len(result["runs"]), 3)
		self.assertGreaterEqual(result["n_events"] + result["n_censored"], 3)

	def test_survival_analysis_requires_at_least_two_runs_with_a_shift(self):
		run = run_architecture(self.architecture.name, seed=1200, episode_count=2)["run"]  # no regime shift
		with self.assertRaises(frappe.ValidationError):
			get_survival_analysis_data([run])
