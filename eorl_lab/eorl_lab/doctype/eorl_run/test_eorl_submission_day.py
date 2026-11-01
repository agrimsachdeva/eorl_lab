"""Tests for the submission-day build (EORL_SUBMISSION_DAY_IMPLEMENTATION_PLAN.md).

Pure-function tests come first and use hand-computed values. The
integration tests at the end run real scripted and bounded-rational
episodes against ERPNext."""
import hashlib
import itertools
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import adaptation, attribute_coherence, constructs, interpretation, paths, repertoire, stats, taxonomy
from eorl_lab.erp.stock import _quality_draw_key
from eorl_lab.providers.bounded_rational import BoundedRationalProvider, quality_evidence
from eorl_lab.runtime import orchestrator
from eorl_lab.scenarios import order_to_cash, procurement


def _tool(episode, tool, actor="A", payload=None):
	return {"event_type": "tool_result", "episode": episode, "target_id": tool, "actor_slot": actor,
		"actor_instance_id": actor, "success": 1, "payload_json": json.dumps(payload or {})}


class TestSequenceScopes(FrappeTestCase):
	def test_consequential_view_drops_reads_and_annotates_supplier(self):
		events = [
			_tool("E1", "get_supplier_options"), _tool("E1", "create_purchase_order", payload={"supplier": "S1"}),
			_tool("E1", "get_purchase_order"), _tool("E1", "submit_purchase_order"), _tool("E1", "finish_turn"),
		]
		self.assertEqual(len(paths.process_path(events)), 5)
		self.assertEqual(
			paths.process_path(events, scope="consequential_actions"),
			["PURCHASE_ORDER:create_purchase_order[S1]", "APPROVAL:submit_purchase_order"],
		)
		self.assertEqual(paths.process_path(events, scope="write_actions"), paths.process_path(events, scope="consequential_actions"))
		self.assertEqual(paths.process_path(events, scope="actor_function_actions"), ["A:create_purchase_order", "A:submit_purchase_order"])

	def test_all_actions_view_is_unchanged_and_unannotated(self):
		events = [_tool("E1", "create_purchase_order", payload={"supplier": "S1"})]
		self.assertEqual(paths.process_path(events), ["PURCHASE_ORDER:create_purchase_order"])

	def test_optional_read_changes_all_actions_but_not_consequential_entropy(self):
		from eorl_lab.analysis.sequence import sequence_entropy

		with_read = [_tool("E1", "get_receipt_status"), _tool("E1", "create_purchase_invoice")]
		without = [_tool("E2", "create_purchase_invoice")]
		eps = [with_read, without]
		self.assertAlmostEqual(sequence_entropy([paths.process_path(e) for e in eps]), 1.0)
		self.assertAlmostEqual(sequence_entropy([paths.process_path(e, scope="consequential_actions") for e in eps]), 0.0)

	def test_unknown_scope_is_rejected(self):
		with self.assertRaises(ValueError):
			paths.process_path([_tool("E1", "create_purchase_order")], scope="interesting_actions")

	def test_scope_metric_name(self):
		self.assertEqual(taxonomy.scope_metric_name("sequence_entropy", "all_actions"), "sequence_entropy")
		self.assertEqual(taxonomy.scope_metric_name("sequence_entropy", "write_actions"), "sequence_entropy@write_actions")


class TestAttributeCoherence(FrappeTestCase):
	def test_hand_computed_values(self):
		events = [
			_tool("E1", "create_purchase_order", "P", {"supplier": "S1"}),
			_tool("E1", "submit_purchase_order", "M"),
			_tool("E1", "create_purchase_receipt", "W"),
		]
		c = attribute_coherence.attribute_coherence(events)
		self.assertEqual(c["actor"], 0.0)  # three different actors
		self.assertEqual(c["counterparty"], 1.0)  # S1 carried forward through the episode
		self.assertEqual(c["object_type"], 0.5)  # purchase_order, purchase_order, purchase_receipt
		self.assertEqual(c["decision_domain"], 0.0)  # sourcing, approval, receiving
		self.assertAlmostEqual(c["composite"], sum(c[a] for a in attribute_coherence.ATTRIBUTES) / 8)

	def test_pairs_never_span_episodes(self):
		events = [_tool("E1", "create_purchase_order", "P"), _tool("E2", "create_purchase_order", "Q")]
		self.assertIsNone(attribute_coherence.attribute_coherence(events)["actor"])


class TestRepertoireAndAdaptation(FrappeTestCase):
	A, B, C = ["x", "a"], ["x", "b"], ["x", "c"]

	def test_three_sets_are_kept_apart(self):
		ok, bad = {"success": True, "utility": 1.0}, {"success": True, "utility": 0.5}
		paths_ = [self.A, self.B, self.A, self.A, self.B, self.C]
		outcomes = [ok, ok, ok, bad, ok, ok]
		phases = ["warmup", "stable", "stable", "shock", "shock", "shock"]
		r = repertoire.adaptive_repertoire(paths_, outcomes, phases)
		self.assertEqual(r["observed_path_count"], 3)
		self.assertEqual(r["viable_path_count"], 3)
		self.assertEqual(r["pre_shock_repertoire_size"], 2)
		self.assertEqual(r["adaptive_repertoire_utilization"], 0.5)  # B reused viably, A not
		self.assertEqual(r["repertoire_retention"], 1.0)  # both pre-shock paths seen again
		self.assertAlmostEqual(r["post_shock_novel_path_rate"], 1 / 3)  # C
		self.assertEqual(r["repertoire_activation_latency"], 1)  # B (not the pre-shock modal A) at offset 1
		self.assertAlmostEqual(r["post_shock_reuse_rate"], 0.5)

	def test_utility_below_threshold_is_not_viable(self):
		self.assertFalse(repertoire.is_viable_v2({"success": True, "utility": 0.85}))
		self.assertTrue(repertoire.is_viable_v2({"success": True, "utility": 0.95}))
		self.assertFalse(repertoire.is_viable_v2({"success": False}))
		self.assertEqual(repertoire.episode_utility({"success": True, "quality_passed": False}), 0.5)

	def test_shock_adaptation(self):
		ok, bad = {"success": True, "utility": 1.0}, {"success": True, "utility": 0.6}
		paths_ = [self.A, self.A, self.A, self.B, self.B, self.B, self.B]
		outcomes = [ok, ok, bad, ok, ok, ok, ok]
		phases = ["warmup", "stable", "shock", "shock", "shock", "shock", "shock"]
		r = adaptation.shock_adaptation(paths_, outcomes, phases, ["S1", "S1", "S1", "S2", "S2", "S2", "S2"])
		self.assertEqual(r["episodes_to_first_adaptive_path"], 1)
		self.assertEqual(r["episodes_to_stable_new_path"], 1)
		self.assertAlmostEqual(r["performance_deficit"], 0.4)
		self.assertEqual(r["post_shock_supplier_distribution"], {"S1": 1, "S2": 4})


class TestConstructMeasures(FrappeTestCase):
	def test_information_asymmetry(self):
		events = [_tool("E1", "t", "A", {"x": 1, "y": 2}), _tool("E1", "t", "B", {"y": 1, "z": 2})]
		self.assertAlmostEqual(constructs.information_asymmetry(events)["asymmetry"], 1 - 1 / 3)
		self.assertIsNone(constructs.information_asymmetry(events[:1]))

	def test_centralization(self):
		self.assertEqual(constructs.authority_centralization({"a": {"approval": True}})["centralization"], 1.0)
		spread = constructs.authority_centralization({"a": {"approval": True}, "b": {"approval": True}})
		self.assertAlmostEqual(spread["centralization"], 0.0)

	def test_specialization(self):
		r = constructs.tool_breadth_specialization({"a": ["t1"], "b": ["t2"]})
		self.assertAlmostEqual(r["specialization"], 0.5)
		self.assertEqual(constructs.tool_breadth_specialization({"a": ["t1", "t2", "finish_turn"]})["specialization"], 0.0)

	def test_communication_centralization(self):
		self.assertAlmostEqual(constructs.communication_centralization({"hub": {"a": 1, "b": 1, "c": 1}}), 1.0)
		ring = {"a": {"b": 1}, "b": {"c": 1}, "c": {"a": 1}}
		self.assertAlmostEqual(constructs.communication_centralization(ring), 0.0)
		self.assertIsNone(constructs.communication_centralization({"a": {"b": 1}}))

	def test_registry_has_at_least_five_executable_constructs(self):
		from eorl_lab.patches.v2_construct_registry_measures import execute

		execute()
		executable = frappe.get_all("EORL Construct", filters={"status": "executable"}, pluck="name")
		self.assertGreaterEqual(len(executable), 5)
		for name in executable:
			self.assertTrue(callable(frappe.get_doc("EORL Construct", name).resolve_measurement_function()))


class TestInference(FrappeTestCase):
	def test_bootstrap_ci_is_seeded_and_brackets_the_estimate(self):
		a, b = [1.0, 2.0, 3.0, 4.0, 5.0], [3.0, 4.0, 5.0, 6.0, 8.0]
		one = stats.hedges_g_bootstrap_ci(a, b, seed=7)
		self.assertEqual(one, stats.hedges_g_bootstrap_ci(a, b, seed=7))
		self.assertLess(one["ci_low"], one["effect_size"])
		self.assertTrue(one["method"].startswith("bootstrap_"))
		self.assertEqual(stats.hedges_g_bootstrap_ci([1, 1], [1, 1])["method"], "undefined")

	def test_multiplicity_adjustment_matches_holm_by_hand(self):
		r = stats.adjust_p_values([0.01, 0.04, 0.03], "holm")
		self.assertEqual([round(p, 6) for p in r["adjusted_p"]], [0.03, 0.06, 0.06])
		self.assertEqual(stats.adjust_p_values([0.01, 0.02], "none")["adjusted_p"], [0.01, 0.02])
		bonf = stats.adjust_p_values([0.01, 0.02, None], "bonferroni")
		self.assertEqual(bonf["family_size"], 2)
		self.assertIsNone(bonf["adjusted_p"][2])

	def test_power_grid_is_deterministic_for_both_designs(self):
		for design in ("independent", "paired"):
			first = stats.power_grid([0.5, 0.8], [10], design=design, n_simulations=200, seed=11)
			self.assertEqual(first, stats.power_grid([0.5, 0.8], [10], design=design, n_simulations=200, seed=11))
			self.assertLess(first[0]["power"], first[1]["power"])

	def test_every_outcome_combination_maps_to_a_label(self):
		cells = set()
		for direction, p, diff, equivalent in itertools.product(
			interpretation.DIRECTIONS, [0.01, 0.5, None], [-1.0, 1.0, None], [True, False, None]
		):
			verdict = interpretation.classify(expected_direction=direction, p_value=p, mean_diff=diff, equivalent=equivalent)
			self.assertIn(verdict["label"], interpretation.LABELS)
			cells.add(verdict["cell"])
		self.assertEqual(len(cells), 6)

	def test_registered_rules_override_defaults(self):
		verdict = interpretation.classify(expected_direction="a_greater", p_value=0.5, mean_diff=0.0, equivalent=True,
			rules={"equivalence_rule": "inconclusive"})
		self.assertEqual(verdict["label"], "inconclusive")
		with self.assertRaises(ValueError):
			interpretation.classify(expected_direction="a_greater", p_value=0.5, mean_diff=0, rules={"support_rule": "yes"})

	def test_combination_rules(self):
		self.assertEqual(interpretation.combine(["consistent", "inconclusive"], "AND")["label"], "inconclusive")
		self.assertEqual(interpretation.combine(["consistent", "inconclusive"], "OR")["label"], "consistent")
		self.assertEqual(interpretation.combine(["consistent", "inconsistent"], "weighted", [3, 1])["label"], "inconclusive")
		self.assertEqual(interpretation.combine(["consistent", "not_evaluated"], "OR")["label"], "not_evaluated")
		self.assertIsNone(interpretation.combine(["consistent"], "separate")["label"])


class TestScenarioAndOutcomeModel(FrappeTestCase):
	def test_hash_of_an_unshocked_case_is_unchanged(self):
		legacy = dict(procurement.BASE_CASE, case_id="CASE-0042-0003", episode=3, seed=42,
			qty=procurement.QTY_BASE + procurement.QTY_STEP * ((42 + 3) % procurement.QTY_CYCLE))
		expected = hashlib.sha256(json.dumps(legacy, sort_keys=True).encode("utf-8")).hexdigest()
		self.assertEqual(procurement.generate_case(42, 3)["case_hash"], expected)

	def test_supplier_reversal_changes_latent_quality_only_after_trigger(self):
		shift = {"trigger_episode": 3, "parameter_delta_json": {
			"pre_shock_latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.95}},
			"post_shock_latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.58}},
		}}
		self.assertEqual(procurement.generate_case(1, 2, shift)["latent_ground_truth"]["Bloomington Dairy"]["quality_probability"], 0.95)
		self.assertEqual(procurement.generate_case(1, 3, shift)["latent_ground_truth"]["Bloomington Dairy"]["quality_probability"], 0.58)
		self.assertEqual(procurement.BASE_CASE["latent_ground_truth"]["Bloomington Dairy"]["quality_probability"], 0.89)
		self.assertEqual(procurement.exogenous_state(procurement.generate_case(1, 3, shift), shift)["regime"], "post_shock")

	def test_matched_draw_ignores_document_names(self):
		case = procurement.generate_case(5, 2)
		self.assertEqual(_quality_draw_key(case, "S", "MAT-PRE-1"), _quality_draw_key(case, "S", "MAT-PRE-2"))
		self.assertNotEqual(_quality_draw_key(case, "S", "X"), _quality_draw_key(case, "T", "X"))
		legacy = procurement.generate_case(5, 2, outcome_model="receipt_keyed_v1")
		self.assertNotEqual(_quality_draw_key(legacy, "S", "MAT-PRE-1"), _quality_draw_key(legacy, "S", "MAT-PRE-2"))

	def test_order_to_cash_case_is_deterministic(self):
		self.assertEqual(order_to_cash.generate_case(3, 1), order_to_cash.generate_case(3, 1))
		self.assertNotIn("payment_reliability", json.dumps(order_to_cash.exogenous_state(order_to_cash.generate_case(3, 1))["customer"]))


class TestBoundedRationalEngine(FrappeTestCase):
	def test_learns_from_its_own_inspection_feedback(self):
		memory = [{"action": "ordered_from:A;quality:failed", "success": 1}, {"action": "ordered_from:A;quality:failed", "success": 1}]
		self.assertEqual(quality_evidence(memory), {"A": [0, 2]})
		provider = BoundedRationalProvider(exploration_rate=0.0)
		supplier, _basis, _a = provider._choose_supplier({"case_id": "C", "seed": 1}, {"candidate_suppliers": ["A", "B"]}, memory)
		self.assertEqual(supplier, "B")

	def test_without_feedback_keeps_the_first_supplier(self):
		provider = BoundedRationalProvider(exploration_rate=0.0)
		memory = [{"action": "ordered_from:A", "success": 1}]  # a specialist's record: no inspection result
		supplier, _b, _a = provider._choose_supplier({"case_id": "C", "seed": 1}, {"candidate_suppliers": ["A", "B"]}, memory)
		self.assertEqual(supplier, "A")

	def test_check_draws_are_matched_across_roles(self):
		provider = BoundedRationalProvider()
		case = {"case_id": "CASE-1", "seed": 1}
		self.assertEqual(provider._wants_check({"case": case}, "confirm_receipt"), provider._wants_check({"case": case}, "confirm_receipt"))


class TestFailureTaxonomy(FrappeTestCase):
	def test_classification(self):
		self.assertEqual(orchestrator._classify_provider_failure(RuntimeError("Read timed out")), "model_timeout")
		self.assertEqual(orchestrator._classify_provider_failure(RuntimeError("model returned no tool call")), "model_parse_error")
		self.assertEqual(orchestrator._classify_tool_failure(frappe.ValidationError("bad")), "erp_validation_error")
		self.assertEqual(orchestrator._classify_tool_failure(KeyError("x")), "tool_error")
		self.assertTrue({"model_timeout", "infrastructure_error"} <= orchestrator.RETRYABLE_FAILURE_TYPES)

	def test_stage_gate(self):
		from eorl_lab.routines import resolve_routine

		gate = orchestrator._stage_gate(resolve_routine("Procure-to-Pay"))
		self.assertIn("create_purchase_order", gate({}))
		self.assertNotIn("submit_purchase_order", gate({}))
		self.assertIn("submit_purchase_order", gate({"purchase_order": "PO-1"}))
		self.assertEqual(gate({"purchase_order": 1, "purchase_order_submitted": 1, "purchase_receipt_submitted": 1,
			"payment_entry_submitted": 1}), {"finish_turn"})


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

P2P = {
	"purchasing_agent": ("Purchasing Agent", 0, 0, 0, ["get_supplier_options", "create_purchase_order"]),
	"purchasing_manager_agent": ("Purchasing Manager Agent", 1, 1, 0, ["get_purchase_order", "submit_purchase_order"]),
	"warehouse_agent": ("Warehouse Agent", 1, 0, 1, ["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt",
		"inspect_received_goods", "escalate_quality_exception", "message_agent"]),
	"accounts_payable_agent": ("Accounts Payable Agent", 1, 0, 0, ["get_receipt_status", "create_purchase_invoice",
		"submit_purchase_invoice", "create_payment_entry", "submit_payment_entry"]),
}
BROAD_TOOLS = sorted({t for spec in P2P.values() for t in spec[4]})


class TestSubmissionDayIntegration(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from eorl_lab.routines import seed_routine_templates

		seed_routine_templates()
		order_to_cash.ensure_master_data()
		profile = frappe.get_doc({"doctype": "EORL Model Profile", "profile_name": "Test SD Scripted", "provider": "deterministic",
			"enabled": 1}).insert(ignore_if_duplicate=True)
		cls.memory = frappe.get_doc({"doctype": "EORL Memory Profile", "profile_name": "Test SD Episodic", "local_memory_enabled": 1,
			"local_backend": "episodic", "local_top_k": 3}).insert(ignore_if_duplicate=True).name

		def policy(name, submit, approve, message, tools):
			return frappe.get_doc({"doctype": "EORL Tool Policy", "policy_name": name, "may_submit_documents": submit,
				"may_approve": approve, "may_message_agents": message,
				"allowed_semantic_tools": [{"tool_name": t} for t in tools]}).insert(ignore_if_duplicate=True).name

		def agent(name, role, pol, memory=None):
			return frappe.get_doc({"doctype": "EORL Agent Template", "template_name": name, "organizational_role": role,
				"model_profile": profile.name, "tool_policy": pol, "memory_profile": memory}).insert(ignore_if_duplicate=True).name

		def arch(name, mode, slots, **extra):
			if not frappe.db.exists("EORL Architecture", name):
				frappe.get_doc({"doctype": "EORL Architecture", "architecture_name": name, "coordination_mode": mode,
					"actor_slots": [{"slot_id": k, "agent_template": v} for k, v in slots.items()], **extra}).insert()
			return name

		spec_slots = {k: agent(f"Test SD {role}", role, policy(f"Test SD {role} Policy", s, a, m, tools))
			for k, (role, s, a, m, tools) in P2P.items()}
		broad_policy = policy("Test SD Broad Policy", 1, 1, 1, BROAD_TOOLS)
		cls.specialist = arch("Test SD Specialist", "specialist_handoff", spec_slots)
		cls.broad = arch("Test SD Broad", "broad_autonomy", {"general_purchasing_agent": agent("Test SD Broad Agent", "General Purchasing Agent", broad_policy, cls.memory)})
		cls.broad_nomem = arch("Test SD Broad No Memory", "broad_autonomy", {"general_purchasing_agent": agent("Test SD Broad Agent NM", "General Purchasing Agent", broad_policy)})
		cls.matched = arch("Test SD Broad Matched", "broad_autonomy", {"general_purchasing_agent": "Test SD Broad Agent"}, stage_gated_tools=1)

		o2c = {"sales_agent": ("Sales Agent", ["get_customer_order", "create_sales_order", "submit_sales_order"]),
			"fulfillment_agent": ("Fulfillment Agent", ["get_sales_order", "create_delivery_note", "submit_delivery_note"]),
			"billing_agent": ("Billing Agent", ["get_delivery_status", "create_sales_invoice", "submit_sales_invoice",
				"create_customer_payment", "submit_customer_payment"])}
		o2c_slots = {k: agent(f"Test SD {role}", role, policy(f"Test SD {role} Policy", 1, 0, 0, tools)) for k, (role, tools) in o2c.items()}
		o2c_broad = agent("Test SD General Order Agent", "General Order Agent",
			policy("Test SD General Order Policy", 1, 1, 0, [t for _r, ts in o2c.values() for t in ts]))
		cls.o2c_specialist = arch("Test SD O2C Specialist", "specialist_handoff", o2c_slots, routine_template="Order-to-Cash")
		cls.o2c_broad = arch("Test SD O2C Broad", "broad_autonomy", {"general_order_agent": o2c_broad}, routine_template="Order-to-Cash")

		if not frappe.db.exists("EORL Regime Shift", "Test SD Supplier Reversal"):
			frappe.get_doc({"doctype": "EORL Regime Shift", "shift_name": "Test SD Supplier Reversal", "trigger_episode": 3,
				"shift_type": "abrupt", "hidden_from_agents": 1, "parameter_delta_json": json.dumps({
					"pre_shock_latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.99}},
					"post_shock_latent_ground_truth": {"Bloomington Dairy": {"quality_probability": 0.01},
						"Indiana Foods Inc": {"quality_probability": 0.99}}})}).insert()

	def test_identical_action_meets_identical_exogenous_outcome(self):
		from eorl_lab.demonstrations.submission_day import verify_matched_outcomes

		a = orchestrator.run_architecture(self.specialist, seed=9301, episode_count=4)
		b = orchestrator.run_architecture(self.broad, seed=9301, episode_count=4)
		check = verify_matched_outcomes(a["run"], b["run"])
		self.assertEqual(check["episodes_compared"], 4)
		self.assertEqual(check["match_rate"], 1.0)

	def test_second_routine_runs_through_the_same_orchestrator(self):
		from eorl_lab.api.process import get_process_explorer_data

		for architecture in (self.o2c_specialist, self.o2c_broad):
			result = orchestrator.run_architecture(architecture, seed=9302, episode_count=1)
			self.assertTrue(result["outcome"]["success"], result["outcome"].get("failure_reason"))
			self.assertTrue(result["outcome"]["customer_payment"])
			run = frappe.get_doc("EORL Run", result["run"])
			self.assertEqual(run.routine_template, "Order-to-Cash")
			data = get_process_explorer_data(result["run"])
			self.assertIn("BILLING:create_sales_invoice", {e["to"] for e in data["dfg_edges"]})

	def test_matched_tools_condition_completes_and_records_telemetry(self):
		result = orchestrator.run_architecture(self.matched, seed=9303, episode_count=1)
		self.assertTrue(result["outcome"]["success"], result["outcome"].get("failure_reason"))
		run = frappe.get_doc("EORL Run", result["run"])
		self.assertGreater(run.model_calls, 5)
		self.assertGreater(run.wallclock_seconds, 0)
		self.assertTrue(run.code_commit)
		self.assertEqual(run.actor_engine, "scripted_deterministic")

	def test_memory_manipulation_changes_only_memory_and_drives_adaptation(self):
		from eorl_lab.api.metrics import compute_run_metrics
		from eorl_lab.api.reviewer import configuration_difference

		with_memory = orchestrator.run_architecture(self.broad, seed=9304, episode_count=6, regime_shift="Test SD Supplier Reversal",
			actor_engine="bounded_rational")
		without = orchestrator.run_architecture(self.broad_nomem, seed=9304, episode_count=6, regime_shift="Test SD Supplier Reversal",
			actor_engine="bounded_rational")
		diff = configuration_difference(with_memory["run"], without["run"])["differing_fields"]
		self.assertTrue(diff)
		self.assertTrue(all("memory_profile_config" in field for field in diff), diff)

		m = compute_run_metrics(with_memory["run"])["metrics"]
		n = compute_run_metrics(without["run"])["metrics"]
		self.assertIn("Indiana Foods Inc", m["post_shock_supplier_distribution"])
		self.assertGreater(m["post_shock_mean_utility"], n["post_shock_mean_utility"])
		self.assertIn("adaptive_repertoire_utilization", m)

	def test_expected_and_unexpected_denials(self):
		policy = frappe.get_doc({"doctype": "EORL Tool Policy", "policy_name": "Test SD Truncated Policy", "may_submit_documents": 1,
			"may_approve": 1, "may_message_agents": 1, "allowed_semantic_tools": [{"tool_name": t} for t in BROAD_TOOLS if "payment" not in t]}).insert(ignore_if_duplicate=True)
		agent = frappe.get_doc({"doctype": "EORL Agent Template", "template_name": "Test SD Truncated Agent", "organizational_role": "General Purchasing Agent",
			"model_profile": "Test SD Scripted", "tool_policy": policy.name}).insert(ignore_if_duplicate=True)
		if not frappe.db.exists("EORL Architecture", "Test SD Truncated"):
			frappe.get_doc({"doctype": "EORL Architecture", "architecture_name": "Test SD Truncated", "coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": agent.name}]}).insert()
		unexpected = orchestrator.run_architecture("Test SD Truncated", seed=9305)
		self.assertEqual(frappe.db.get_value("EORL Run", unexpected["run"], "failure_type"), "authority_denial_unexpected")
		expected = orchestrator.run_architecture("Test SD Truncated", seed=9305, expected_denial_codes=["TOOL_NOT_IN_POLICY"])
		self.assertEqual(frappe.db.get_value("EORL Run", expected["run"], "failure_type"), "authority_denial_expected")
		self.assertEqual(frappe.db.get_value("EORL Run", expected["run"], "retryable"), 0)

	def test_queued_run_and_cancellation(self):
		run = frappe.get_doc({"doctype": "EORL Run", "run_seed": 9306, "status": "queued"}).insert()
		orchestrator.run_queued(run.name, self.broad, 9306, 1)
		self.assertEqual(frappe.db.get_value("EORL Run", run.name, "status"), "completed")

		cancelled = frappe.get_doc({"doctype": "EORL Run", "run_seed": 9307, "status": "queued"}).insert()
		frappe.cache().set_value(f"eorl_cancel:{cancelled.name}", 1)
		try:
			orchestrator.run_queued(cancelled.name, self.broad, 9307, 1)
			self.assertEqual(frappe.db.get_value("EORL Run", cancelled.name, "status"), "cancelled")
		finally:
			frappe.cache().delete_value(f"eorl_cancel:{cancelled.name}")

	def test_viewer_role_has_no_write_permission_on_any_eorl_doctype(self):
		writable = frappe.get_all("DocPerm", filters={"role": "EORL Viewer", "parent": ["like", "EORL %"]},
			fields=["parent", "write", "create", "delete", "submit", "cancel"])
		self.assertTrue(writable)
		for perm in writable:
			self.assertFalse(any([perm.write, perm.create, perm.delete, perm.submit, perm.cancel]), perm.parent)

	def test_comparison_without_create_permission_persists_nothing(self):
		from unittest.mock import patch

		from eorl_lab.api.analysis import compare_groups

		runs_a = [orchestrator.run_architecture(self.specialist, seed=s, episode_count=1)["run"] for s in (9311, 9312)]
		runs_b = [orchestrator.run_architecture(self.broad_nomem, seed=s, episode_count=1)["run"] for s in (9311, 9312)]
		plan = frappe.get_doc({"doctype": "EORL Analysis Plan", "plan_name": "Test SD viewer plan", "outcome_metric": "actor_continuity",
			"analysis_unit": "run", "permutation_iterations": 200, "bootstrap_iterations": 200}).insert(ignore_if_duplicate=True)
		results_before = frappe.db.count("EORL Analysis Result")
		metrics_before = frappe.db.count("EORL Metric")
		with patch("frappe.has_permission", return_value=False):
			out = compare_groups(plan.name, runs_a, runs_b)
		self.assertFalse(out["persisted"])
		self.assertEqual(out["analysis_result_names"], [])
		self.assertEqual(frappe.db.count("EORL Analysis Result"), results_before)
		self.assertEqual(frappe.db.count("EORL Metric"), metrics_before)
		self.assertIn("ci_low", out["standardized_effect_ci"])

	def test_family_adjustment_writes_adjusted_p(self):
		from eorl_lab.api.analysis import apply_family_adjustment

		names = []
		for i, p in enumerate((0.01, 0.04)):
			plan = frappe.get_doc({"doctype": "EORL Analysis Plan", "plan_name": f"Test SD family plan {i}", "outcome_metric": "x",
				"analysis_unit": "run", "multiple_testing_family": "Test SD family", "adjustment_method": "holm"}).insert(ignore_if_duplicate=True)
			names.append(frappe.get_doc({"doctype": "EORL Analysis Result", "analysis_plan": plan.name, "test_family": "welch_t",
				"is_primary_test": 1, "p_value": p}).insert().name)
		out = apply_family_adjustment("Test SD family")
		self.assertEqual(out["family_size"], 2)
		self.assertAlmostEqual(frappe.db.get_value("EORL Analysis Result", names[0], "adjusted_p_value"), 0.02)
		self.assertAlmostEqual(frappe.db.get_value("EORL Analysis Result", names[1], "adjusted_p_value"), 0.04)

	def test_interpretation_reads_raw_p_when_there_is_no_family(self):
		"""Frappe stores an empty Float as 0, so an unadjusted result's
		adjusted_p_value column reads 0.0; it must not be taken for p = 0."""
		from eorl_lab.api.analysis import evaluate_experiment_interpretation

		if not frappe.db.exists("EORL Experiment", "Test SD interpretation experiment"):
			frappe.get_doc({"doctype": "EORL Experiment", "experiment_name": "Test SD interpretation experiment",
				"interpretation_combination": "AND"}).insert()
		plan = frappe.get_doc({"doctype": "EORL Analysis Plan", "plan_name": "Test SD interpretation plan", "outcome_metric": "x",
			"analysis_unit": "run", "experiment": "Test SD interpretation experiment", "expected_direction": "a_greater"}).insert(ignore_if_duplicate=True)
		frappe.get_doc({"doctype": "EORL Analysis Result", "analysis_plan": plan.name, "test_family": "welch_t", "is_primary_test": 1,
			"p_value": 0.9, "mean_a": 1.0, "mean_b": 0.5, "diagnostics_json": json.dumps({"test": "welch_t", "p_value": 0.9})}).insert()
		out = evaluate_experiment_interpretation("Test SD interpretation experiment")
		self.assertEqual(out["plans"][0]["label"], "inconclusive")

	def test_undefined_metric_is_flagged_not_read_as_zero(self):
		from eorl_lab.api.analysis import _run_level_metric

		run = orchestrator.run_architecture(self.broad, seed=9321, episode_count=1)["run"]
		from eorl_lab.api.metrics import compute_run_metrics

		self.assertIsNone(compute_run_metrics(run)["metrics"]["information_asymmetry"])  # one actor
		self.assertEqual(frappe.db.get_value("EORL Metric", {"run": run, "metric_name": "information_asymmetry"}, "value_undefined"), 1)
		with self.assertRaises(frappe.ValidationError):
			_run_level_metric(run, "information_asymmetry")

	def test_success_rate_is_not_utility(self):
		from eorl_lab.api.metrics import compute_run_metrics

		run = orchestrator.run_architecture(self.broad, seed=9322, episode_count=3, regime_shift="Test SD Supplier Reversal")["run"]
		m = compute_run_metrics(run)["metrics"]
		self.assertEqual(m["success_rate"], 1.0)
		self.assertLess(m["mean_utility"], 1.0)  # episode 3 meets the reversal (quality 0.01)
