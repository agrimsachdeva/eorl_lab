import frappe
from frappe.utils import now_datetime

from eorl_lab.analysis import coherence, networks, paths, recovery, repertoire, sequence

METRIC_VERSION = "v1"

_REPERTOIRE_DEPENDENT_METRICS = {
	"viable_unique_path_count", "viable_path_entropy", "concentration_top1",
	"proportion_repertoire_reused_after_shock", "novel_viable_paths_after_shock",
	"path_extinction_rate", "change_in_path_concentration_top1",
}


def _metric_version(metric_name: str) -> str:
	if metric_name in _REPERTOIRE_DEPENDENT_METRICS:
		return f"{METRIC_VERSION}+viability:{repertoire.VIABILITY_CRITERION_VERSION}"
	return METRIC_VERSION


def _episode_data(run_name: str):
	"""Fetch per-episode events/outcomes/phases for a run as plain
	dicts/lists -- the same shape the pure eorl_lab.analysis functions
	expect. This is the only place in the metrics pipeline that touches
	Frappe; everything downstream works equally well on an exported
	JSONL bundle outside Frappe (spec section 17's closing requirement)."""
	episodes = frappe.get_all(
		"EORL Episode",
		filters={"run": run_name},
		fields=["name", "episode_number", "phase", "outcome_json"],
		order_by="episode_number asc",
	)
	all_events = frappe.get_all(
		"EORL Event",
		filters={"run": run_name},
		fields=[
			"episode", "event_type", "run", "actor_slot", "actor_instance_id",
			"target_id", "success", "wallclock_timestamp",
		],
		order_by="sequence_no asc",
	)
	events_by_episode: dict = {}
	for event in all_events:
		events_by_episode.setdefault(event.episode, []).append(event)

	episode_paths, episode_events, outcomes, phases = [], [], [], []
	for ep in episodes:
		events_for_episode = events_by_episode.get(ep.name, [])
		episode_events.append(events_for_episode)
		episode_paths.append(paths.process_path(events_for_episode))
		outcomes.append(frappe.parse_json(ep.outcome_json or "{}"))
		phases.append(ep.phase)

	return episode_events, episode_paths, outcomes, phases


def _save_metric(run_name, metric_name, value, episode=None, phase=None):
	numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
	frappe.get_doc(
		{
			"doctype": "EORL Metric",
			"run": run_name,
			"episode": episode,
			"phase": phase,
			"metric_name": metric_name,
			"metric_value": value if numeric else None,
			"metric_version": _metric_version(metric_name),
			"computed_at": now_datetime(),
			"metric_json": None if numeric or value is None else frappe.as_json(value),
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def compute_run_metrics(run_name: str) -> dict:
	"""Computes and persists the Milestone 7 metric set for one run
	(spec section 17.3), via the pure functions in eorl_lab.analysis --
	the same functions anyone could call directly on an exported bundle
	outside Frappe. Milestone 7 deviation: ground-truth-driven
	performance measures (decision accuracy, financial cost) aren't
	computed, because the scenario generator doesn't yet produce
	ground-truth-driven probabilistic outcomes (spec section 11) --
	"performance" here is episode success (1.0/0.0), which is honest but
	currently non-discriminating on demo data where almost everything
	succeeds."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])

	episode_events, episode_paths, outcomes, phases = _episode_data(run_name)
	performance = [1.0 if o.get("success") else 0.0 for o in outcomes]
	all_events_flat = [e for group in episode_events for e in group]

	computed = {}

	def record(name, value):
		computed[name] = value
		_save_metric(run_name, name, value)

	# Outcome (SOTA Milestone 5: a named, persisted run-level metric --
	# previously only computed ad hoc inline by compare_runs below, not
	# available for eorl_lab.api.analysis.compare_groups to read as an
	# EORL Analysis Plan.outcome_metric).
	record("success_rate", (sum(performance) / len(performance)) if performance else None)

	# Routine structure
	record("unique_sequence_count", sequence.unique_sequence_count(episode_paths))
	record("sequence_entropy", sequence.sequence_entropy(episode_paths))
	record("modal_path_share", sequence.modal_path_share(episode_paths))
	record("transition_entropy", sequence.transition_entropy(episode_paths))
	record("directly_follows_graph", sequence.directly_follows_graph(episode_paths))

	# Path coherence
	record("actor_switch_rate", coherence.actor_switch_rate(all_events_flat))
	record("actor_continuity", coherence.actor_continuity(all_events_flat))
	record("average_actor_run_length", coherence.average_actor_run_length(all_events_flat))
	record("functional_switch_rate", coherence.functional_switch_rate(all_events_flat))
	record("functional_continuity", coherence.functional_continuity(all_events_flat))
	record("stage_continuity", coherence.stage_continuity(all_events_flat))
	record("repeated_path_probability", coherence.repeated_path_probability(episode_paths))

	# Adaptive repertoire
	record("viable_unique_path_count", len(repertoire.viable_unique_paths(episode_paths, outcomes)))
	record("viable_path_entropy", repertoire.viable_path_entropy(episode_paths, outcomes))
	record("concentration_top1", repertoire.concentration_in_top_k(episode_paths, outcomes, k=1))

	if any(ph in ("shock", "recovery") for ph in phases):
		record(
			"proportion_repertoire_reused_after_shock",
			repertoire.proportion_repertoire_reused_after_shock(episode_paths, outcomes, phases),
		)
		record("novel_viable_paths_after_shock", repertoire.novel_viable_paths_after_shock(episode_paths, outcomes, phases))
		record("path_extinction_rate", repertoire.path_extinction_rate(episode_paths, outcomes, phases))

		# Adaptation
		record("immediate_post_shock_drop", recovery.immediate_post_shock_drop(performance, phases))
		record("episodes_to_recover_90pct", recovery.episodes_to_recover(performance, phases, 0.9))
		record("area_under_recovery_curve", recovery.area_under_recovery_curve(performance, phases))
		record("post_shock_error_rate", recovery.post_shock_error_rate(performance, phases))
		record("change_in_sequence_entropy", recovery.change_in_sequence_entropy(episode_paths, phases))
		record(
			"change_in_path_concentration_top1",
			recovery.change_in_path_concentration(episode_paths, outcomes, phases, k=1),
		)

	# Communication network
	record("communication_network", networks.communication_network(all_events_flat))

	return {"run": run_name, "metrics": computed}


@frappe.whitelist()
def compare_runs(runs) -> list:
	"""Backs the Compare Runs page (spec section 7.8). Milestone 6's raw
	aggregates, now enriched with Milestone 7's real coherence/variety
	metrics (computed inline, not persisted -- compute_run_metrics is
	the entrypoint that persists EORL Metric rows)."""
	if isinstance(runs, str):
		runs = frappe.parse_json(runs)

	comparison = []
	for run_name in runs:
		run_doc = frappe.get_doc("EORL Run", run_name)
		episode_events, episode_paths, outcomes, _phases = _episode_data(run_name)
		all_events_flat = [e for group in episode_events for e in group]
		distinct_actors = {e.actor_slot for group in episode_events for e in group if e.actor_slot}

		comparison.append(
			{
				"run": run_name,
				"status": run_doc.status,
				"run_seed": run_doc.run_seed,
				"episode_count": len(episode_events),
				"success_rate": (sum(1 for o in outcomes if o.get("success")) / len(outcomes)) if outcomes else None,
				"distinct_actor_count": len(distinct_actors),
				"actor_slots": sorted(distinct_actors),
				"event_count": run_doc.event_count,
				"unique_sequence_count": sequence.unique_sequence_count(episode_paths),
				"sequence_entropy": sequence.sequence_entropy(episode_paths),
				"actor_continuity": coherence.actor_continuity(all_events_flat),
				"average_actor_run_length": coherence.average_actor_run_length(all_events_flat),
			}
		)
	return comparison
