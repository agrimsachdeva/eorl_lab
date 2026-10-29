import math

from frappe.tests.utils import FrappeTestCase

from eorl_lab.analysis import coherence, paths, recovery, repertoire, sequence


def _tool_result(run, episode, actor_slot, actor_instance_id, tool_name, success=True):
	return {
		"run": run, "episode": episode, "event_type": "tool_result",
		"actor_slot": actor_slot, "actor_instance_id": actor_instance_id,
		"target_id": tool_name, "success": 1 if success else 0,
		"wallclock_timestamp": "2026-01-01 00:00:00",
	}


class TestProcessPathExtraction(FrappeTestCase):
	def test_extracts_only_tool_result_events_and_maps_stages(self):
		events = [
			{"event_type": "tool_requested", "target_id": "create_purchase_order"},  # ignored
			_tool_result("R1", "R1-EP-1", "Purchasing Agent", "Agent A", "get_supplier_options"),
			_tool_result("R1", "R1-EP-1", "Purchasing Agent", "Agent A", "create_purchase_order"),
			_tool_result("R1", "R1-EP-1", "Warehouse Agent", "Agent B", "create_purchase_receipt"),
		]
		canonical = paths.extract_canonical_events(events)
		self.assertEqual(len(canonical), 3)
		self.assertEqual(canonical[0].process_stage, "SUPPLIER_SEARCH")
		self.assertEqual(canonical[1].process_stage, "PURCHASE_ORDER")
		self.assertEqual(canonical[2].process_stage, "RECEIPT")
		self.assertEqual(canonical[0].order, 1)
		self.assertEqual(canonical[2].order, 3)

		path = paths.process_path(events)
		self.assertEqual(
			path,
			["SUPPLIER_SEARCH:get_supplier_options", "PURCHASE_ORDER:create_purchase_order", "RECEIPT:create_purchase_receipt"],
		)

	def test_unmapped_tool_falls_through_explicitly_not_miscategorized(self):
		events = [_tool_result("R1", "R1-EP-1", "Some Agent", "A", "totally_unknown_tool")]
		canonical = paths.extract_canonical_events(events)
		self.assertEqual(canonical[0].process_stage, "UNMAPPED")


class TestSequenceMetrics(FrappeTestCase):
	def test_identical_paths_give_zero_entropy_and_full_modal_share(self):
		paths_ = [["A", "B"], ["A", "B"], ["A", "B"]]
		self.assertEqual(sequence.unique_sequence_count(paths_), 1)
		self.assertEqual(sequence.sequence_entropy(paths_), 0.0)
		self.assertEqual(sequence.modal_path_share(paths_), 1.0)

	def test_two_equally_common_distinct_paths_give_one_bit_of_entropy(self):
		paths_ = [["A", "B"], ["A", "B"], ["A", "C"], ["A", "C"]]
		self.assertEqual(sequence.unique_sequence_count(paths_), 2)
		self.assertAlmostEqual(sequence.sequence_entropy(paths_), 1.0, places=6)
		self.assertEqual(sequence.modal_path_share(paths_), 0.5)

	def test_directly_follows_graph_counts_transitions(self):
		paths_ = [["A", "B", "C"], ["A", "B", "C"], ["A", "C"]]
		graph = sequence.directly_follows_graph(paths_)
		self.assertEqual(graph["A"]["B"], 2)
		self.assertEqual(graph["A"]["C"], 1)
		self.assertEqual(graph["B"]["C"], 2)


class TestCoherenceMetrics(FrappeTestCase):
	def test_single_continuous_actor_has_zero_switch_rate_and_full_run_length(self):
		events = [
			_tool_result("R1", "EP1", "General Purchasing Agent", "GPA", "get_supplier_options"),
			_tool_result("R1", "EP1", "General Purchasing Agent", "GPA", "create_purchase_order"),
			_tool_result("R1", "EP1", "General Purchasing Agent", "GPA", "submit_purchase_order"),
		]
		self.assertEqual(coherence.actor_switch_rate(events), 0.0)
		self.assertEqual(coherence.actor_continuity(events), 1.0)
		self.assertEqual(coherence.average_actor_run_length(events), 3.0)

	def test_four_specialists_with_one_handoff_each_switch_every_boundary(self):
		events = [
			_tool_result("R1", "EP1", "Purchasing Agent", "PA", "get_supplier_options"),
			_tool_result("R1", "EP1", "Purchasing Agent", "PA", "create_purchase_order"),
			_tool_result("R1", "EP1", "Purchasing Manager Agent", "PMA", "get_purchase_order"),
			_tool_result("R1", "EP1", "Purchasing Manager Agent", "PMA", "submit_purchase_order"),
			_tool_result("R1", "EP1", "Warehouse Agent", "WA", "create_purchase_receipt"),
		]
		# 4 transitions total, 2 are switches (PA->PMA, PMA->WA)
		self.assertAlmostEqual(coherence.actor_switch_rate(events), 2 / 4)
		self.assertAlmostEqual(coherence.average_actor_run_length(events), 5 / 3)  # run lengths [2,2,1]

	def test_broad_autonomy_more_continuous_than_specialist_handoff(self):
		"""The actual discriminating claim behind Milestone 5's
		architecture comparison, proven on synthetic data shaped exactly
		like what the real orchestrator produces."""
		specialist = [
			_tool_result("R1", "EP1", "Purchasing Agent", "PA", "get_supplier_options"),
			_tool_result("R1", "EP1", "Purchasing Agent", "PA", "create_purchase_order"),
			_tool_result("R1", "EP1", "Purchasing Manager Agent", "PMA", "get_purchase_order"),
			_tool_result("R1", "EP1", "Purchasing Manager Agent", "PMA", "submit_purchase_order"),
			_tool_result("R1", "EP1", "Warehouse Agent", "WA", "get_purchase_order"),
			_tool_result("R1", "EP1", "Warehouse Agent", "WA", "create_purchase_receipt"),
			_tool_result("R1", "EP1", "Warehouse Agent", "WA", "submit_purchase_receipt"),
			_tool_result("R1", "EP1", "Accounts Payable Agent", "APA", "get_receipt_status"),
		]
		broad = [
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "get_supplier_options"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "create_purchase_order"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "get_purchase_order"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "submit_purchase_order"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "create_purchase_receipt"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "submit_purchase_receipt"),
			_tool_result("R2", "EP1", "General Purchasing Agent", "GPA", "get_receipt_status"),
		]
		self.assertEqual(coherence.actor_switch_rate(broad), 0.0)
		self.assertGreater(coherence.actor_switch_rate(specialist), coherence.actor_switch_rate(broad))
		self.assertGreater(coherence.average_actor_run_length(broad), coherence.average_actor_run_length(specialist))


class TestRepertoireMetrics(FrappeTestCase):
	def test_viability_requires_outcome_success_not_just_distinctness(self):
		episode_paths = [["A", "B"], ["A", "C"], ["A", "D"]]
		outcomes = [{"success": True}, {"success": False}, {"success": True}]
		viable = repertoire.viable_unique_paths(episode_paths, outcomes)
		# ["A", "C"] is distinct but not viable -- excluded.
		self.assertEqual(viable, {("A", "B"), ("A", "D")})

	def test_path_extinction_and_novel_discovery_around_a_synthetic_shock(self):
		episode_paths = [["X"], ["X"], ["Y"], ["Y"], ["Z"]]
		outcomes = [{"success": True}] * 5
		phases = ["warmup", "stable", "shock", "shock", "recovery"]
		# pre-shock viable: {X}; post-shock viable: {Y, Z}
		self.assertEqual(repertoire.novel_viable_paths_after_shock(episode_paths, outcomes, phases), 2)
		self.assertEqual(repertoire.path_extinction_rate(episode_paths, outcomes, phases), 1.0)
		self.assertEqual(repertoire.proportion_repertoire_reused_after_shock(episode_paths, outcomes, phases), 0.0)

	def test_reuse_when_a_pre_shock_path_reappears_after_shock(self):
		episode_paths = [["X"], ["Y"], ["X"], ["Z"]]
		outcomes = [{"success": True}] * 4
		phases = ["warmup", "stable", "shock", "shock"]
		# pre-shock viable: {X, Y}; post-shock viable: {X, Z}; reused: {X}
		self.assertAlmostEqual(repertoire.proportion_repertoire_reused_after_shock(episode_paths, outcomes, phases), 0.5)


class TestRecoveryMetrics(FrappeTestCase):
	def test_recovery_metrics_on_a_controlled_synthetic_drop_and_recovery(self):
		"""Proves the adaptation math itself is correct, independent of
		whether current live demo data exercises it -- see PROGRESS.md's
		documented finding that today's deterministic policy doesn't
		vary enough to produce real failures around the shock yet."""
		performance = [1.0, 1.0, 0.0, 0.5, 1.0]
		phases = ["warmup", "stable", "shock", "shock", "recovery"]

		self.assertAlmostEqual(recovery.immediate_post_shock_drop(performance, phases), 1.0)  # 1.0 - 0.0
		self.assertEqual(recovery.episodes_to_recover(performance, phases, threshold_fraction=0.9), 2)  # index 2 in post-shock slice = value 1.0
		self.assertAlmostEqual(recovery.area_under_recovery_curve(performance, phases), 1.0 + 0.5 + 0.0)
		self.assertAlmostEqual(recovery.post_shock_error_rate(performance, phases), 1 - (0.0 + 0.5 + 1.0) / 3)

	def test_never_recovers_returns_none(self):
		performance = [1.0, 1.0, 0.2, 0.3]
		phases = ["warmup", "stable", "shock", "shock"]
		self.assertIsNone(recovery.episodes_to_recover(performance, phases, threshold_fraction=0.9))

	def test_change_in_sequence_entropy_reflects_new_variety_after_shock(self):
		episode_paths = [["A"], ["A"], ["B"], ["C"]]
		phases = ["warmup", "stable", "shock", "shock"]
		delta = recovery.change_in_sequence_entropy(episode_paths, phases)
		self.assertGreater(delta, 0)  # pre: entropy 0 (all "A"); post: entropy 1 (B,C evenly split)
		self.assertAlmostEqual(delta, 1.0 - 0.0)
