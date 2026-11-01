import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.api.experiments import get_experiment_summary, launch_pilot, validate_experiment
from eorl_lab.api.runs import mark_ablation


class TestEORLConstructRegistry(FrappeTestCase):
	"""SOTA Milestone 4 (V2 section 20): a reusable library connecting
	theory to implementation. These tests check the registry is
	internally consistent and honest, not that every construct has a
	working metric -- most don't yet, and say so."""

	def test_all_eight_initial_constructs_are_seeded(self):
		expected = {
			"Centralization", "Specialization", "Formalization", "Information asymmetry",
			"Hierarchy", "Transactive memory", "Routine coherence", "Adaptive repertoire",
		}
		seeded = set(frappe.get_all("EORL Construct", pluck="name"))
		self.assertTrue(expected.issubset(seeded), f"missing: {expected - seeded}")

	def test_implemented_constructs_resolve_to_a_real_callable(self):
		for name in ("Routine coherence", "Adaptive repertoire"):
			construct = frappe.get_doc("EORL Construct", name)
			fn = construct.resolve_measurement_function()
			self.assertTrue(callable(fn), f"{name}'s measurement_function must resolve to a callable")

	def test_unimplemented_construct_raises_not_implemented_rather_than_guessing(self):
		# Centralization gained a measurement function on submission day;
		# Formalization is still defined but not measured.
		construct = frappe.get_doc("EORL Construct", "Formalization")
		self.assertFalse(construct.measurement_function)
		with self.assertRaises(NotImplementedError):
			construct.resolve_measurement_function()

	def test_routine_coherence_measurement_function_actually_runs_on_real_events(self):
		from eorl_lab.runtime.orchestrator import run_demo_episode

		model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test Construct Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy", "policy_name": "Test Construct Tool Policy",
				"allowed_semantic_tools": [{"tool_name": t} for t in ("get_supplier_options", "create_purchase_order")],
			}
		).insert(ignore_if_duplicate=True)
		agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Construct Purchasing Agent",
				"organizational_role": "Purchasing Agent", "model_profile": model_profile.name, "tool_policy": policy.name,
			}
		).insert(ignore_if_duplicate=True)

		result = run_demo_episode(agent.name, seed=1)
		events = frappe.get_all(
			"EORL Event", filters={"run": result["run"]}, fields=["event_type", "actor_slot"], order_by="sequence_no asc",
		)
		event_dicts = [dict(e) for e in events]

		construct = frappe.get_doc("EORL Construct", "Routine coherence")
		fn = construct.resolve_measurement_function()
		value = fn(event_dicts)
		self.assertIsInstance(value, float)
		self.assertGreaterEqual(value, 0.0)
		self.assertLessEqual(value, 1.0)


class TestEORLFactorialExperiments(FrappeTestCase):
	"""SOTA Milestone 4 (V2 section 28.7): generalizes EORL Experiment
	from the fixed architecture_a/architecture_b pair to a real N-factor,
	K-level factorial design, without changing the original behavior
	when `factors` is left empty."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test Factorial Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		broad_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy", "policy_name": "Test Factorial Broad Policy",
				"may_submit_documents": 1, "may_approve": 1, "may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in (
					"get_supplier_options", "get_purchase_order", "get_receipt_status",
					"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
					"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
					"create_payment_entry", "submit_payment_entry",
					"inspect_received_goods", "escalate_quality_exception", "message_agent",
				)],
			}
		).insert(ignore_if_duplicate=True)
		broad_agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Factorial General Purchasing Agent",
				"organizational_role": "General Purchasing Agent", "model_profile": self.model_profile.name, "tool_policy": broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.broad_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test Factorial Broad Autonomy",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent.name}],
			}
		).insert(ignore_if_duplicate=True)

		# A second "architecture" level: same broad_autonomy mode, distinct
		# document, enough to prove two cells launch two different
		# architectures -- the factorial machinery doesn't care whether
		# the levels are "interesting" in modeling terms, only that they
		# are genuinely different EORL Architecture documents.
		broad_agent_2 = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Factorial General Purchasing Agent 2",
				"organizational_role": "General Purchasing Agent", "model_profile": self.model_profile.name, "tool_policy": broad_policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.broad_architecture_2 = frappe.get_doc(
			{
				"doctype": "EORL Architecture", "architecture_name": "Test Factorial Broad Autonomy 2",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": broad_agent_2.name}],
			}
		).insert(ignore_if_duplicate=True)

		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift", "shift_name": "Test Factorial Demand Shock",
				"trigger_episode": 2, "parameter_delta_json": frappe.as_json({"qty_multiplier": 1.5}),
			}
		).insert(ignore_if_duplicate=True)

	def _two_by_two_experiment(self, name):
		exp = frappe.get_doc(
			{
				"doctype": "EORL Experiment", "experiment_name": name,
				"architecture_a": self.broad_architecture.name,  # fallback, unused once factors are set
				"episode_count": 2, "repetitions_per_cell": 1, "seed_strategy": "paired", "base_seed": 100,
				"factors": [
					{"factor_name": "architecture", "level_label": "Arch 1", "factor_type": "architecture", "architecture": self.broad_architecture.name, "is_baseline": 1},
					{"factor_name": "architecture", "level_label": "Arch 2", "factor_type": "architecture", "architecture": self.broad_architecture_2.name},
					{"factor_name": "regime", "level_label": "No Shock", "factor_type": "regime_shift", "is_baseline": 1},
					{"factor_name": "regime", "level_label": "Demand Shock", "factor_type": "regime_shift", "regime_shift": self.regime_shift.name},
				],
			}
		).insert(ignore_permissions=True)
		return exp

	def test_cell_count_is_the_product_of_each_factors_level_count(self):
		exp = self._two_by_two_experiment("Test Factorial 2x2 Cell Count")
		self.assertEqual(exp.cell_count(), 4)
		self.assertEqual(exp.total_run_count(), 4)

	def test_old_architecture_a_b_experiments_are_completely_unaffected(self):
		exp = frappe.get_doc(
			{
				"doctype": "EORL Experiment", "experiment_name": "Test Factorial Backward Compat",
				"architecture_a": self.broad_architecture.name, "architecture_b": self.broad_architecture_2.name,
				"episode_count": 1, "repetitions_per_cell": 2,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(exp.factorial_cells(), [])
		self.assertEqual(exp.cell_count(), 2)
		self.assertEqual(exp.total_run_count(), 4)

	def test_launch_pilot_runs_every_cell_of_the_factorial_design(self):
		exp = self._two_by_two_experiment("Test Factorial 2x2 Launch")
		validation = validate_experiment(exp.name)
		self.assertTrue(validation["valid"], validation["errors"])

		result = launch_pilot(exp.name, repetitions=1)
		self.assertEqual(len(result["runs"]), 4)

		architectures_used = {r["architecture"] for r in result["runs"]}
		self.assertEqual(architectures_used, {self.broad_architecture.name, self.broad_architecture_2.name})

		regime_shifts_used = {r["regime_shift"] for r in result["runs"]}
		self.assertEqual(regime_shifts_used, {None, self.regime_shift.name})

		for r in result["runs"]:
			self.assertTrue(r["success"], r)

	def test_paired_seed_strategy_gives_every_cell_in_a_repetition_the_same_seed(self):
		exp = self._two_by_two_experiment("Test Factorial 2x2 Paired Seeds")
		result = launch_pilot(exp.name, repetitions=1)
		seeds = {r["seed"] for r in result["runs"]}
		self.assertEqual(seeds, {100})  # base_seed=100, rep=0, paired -> identical across all 4 cells

	def test_get_experiment_summary_reports_factors_and_focal_construct(self):
		exp = self._two_by_two_experiment("Test Factorial Summary")
		exp.focal_construct = "Adaptive repertoire"
		exp.save()

		summary = get_experiment_summary(exp.name)
		self.assertEqual(summary["cell_count"], 4)
		self.assertEqual(len(summary["factors"]), 4)
		self.assertEqual(summary["focal_construct"], "Adaptive repertoire")

	def test_validate_experiment_rejects_unknown_focal_construct(self):
		exp = self._two_by_two_experiment("Test Factorial Bad Construct")
		exp.focal_construct = None
		exp.db_set("focal_construct", "This Construct Does Not Exist")
		validation = validate_experiment(exp.name)
		self.assertFalse(validation["valid"])
		self.assertTrue(any("focal_construct" in e for e in validation["errors"]))

	def test_validate_experiment_rejects_unknown_architecture_inside_a_factor(self):
		exp = self._two_by_two_experiment("Test Factorial Bad Architecture Factor")
		exp.factors[0].db_set("architecture", "This Architecture Does Not Exist")
		validation = validate_experiment(exp.name)
		self.assertFalse(validation["valid"])


class TestEORLAblationMarking(FrappeTestCase):
	"""SOTA Milestone 4 (V2 section 19): "Provide an interface for
	marking a run as an ablation of another configuration." """

	def setUp(self):
		model_profile = frappe.get_doc(
			{"doctype": "EORL Model Profile", "profile_name": "Test Ablation Deterministic Profile", "provider": "deterministic"}
		).insert(ignore_if_duplicate=True)
		policy = frappe.get_doc(
			{"doctype": "EORL Tool Policy", "policy_name": "Test Ablation Tool Policy"}
		).insert(ignore_if_duplicate=True)
		agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template", "template_name": "Test Ablation Agent",
				"organizational_role": "Purchasing Agent", "model_profile": model_profile.name, "tool_policy": policy.name,
			}
		).insert(ignore_if_duplicate=True)

		self.baseline_run = frappe.get_doc(
			{"doctype": "EORL Run", "run_seed": 1, "status": "completed", "frappe_version": frappe.__version__}
		).insert(ignore_permissions=True)
		self.ablated_run = frappe.get_doc(
			{"doctype": "EORL Run", "run_seed": 1, "status": "completed", "frappe_version": frappe.__version__}
		).insert(ignore_permissions=True)
		self._agent = agent  # unused directly; keeps fixture symmetric with other test files

	def test_mark_ablation_records_baseline_and_mechanism(self):
		result = mark_ablation(self.ablated_run.name, self.baseline_run.name, "memory_disabled")
		self.assertEqual(result["is_ablation_of"], self.baseline_run.name)
		self.assertEqual(result["ablation_mechanism"], "memory_disabled")

		run_doc = frappe.get_doc("EORL Run", self.ablated_run.name)
		self.assertEqual(run_doc.is_ablation_of, self.baseline_run.name)
		self.assertEqual(run_doc.ablation_mechanism, "memory_disabled")

	def test_mark_ablation_emits_a_real_event(self):
		mark_ablation(self.ablated_run.name, self.baseline_run.name, "tool_breadth_reduced")
		events = frappe.get_all(
			"EORL Event", filters={"run": self.ablated_run.name, "event_type": "run_marked_ablation"}, fields=["payload_json"],
		)
		self.assertEqual(len(events), 1)
		payload = frappe.parse_json(events[0].payload_json)
		self.assertEqual(payload["baseline_run"], self.baseline_run.name)
		self.assertEqual(payload["mechanism"], "tool_breadth_reduced")

	def test_mark_ablation_rejects_unknown_baseline(self):
		with self.assertRaises(frappe.ValidationError):
			mark_ablation(self.ablated_run.name, "RUN-DOES-NOT-EXIST", "memory_disabled")

	def test_mark_ablation_rejects_self_reference(self):
		with self.assertRaises(frappe.ValidationError):
			mark_ablation(self.baseline_run.name, self.baseline_run.name, "memory_disabled")
