import frappe

from eorl_lab.analysis import adaptation, attribute_coherence, coherence, paths, recovery, repertoire, sequence, stats, taxonomy
from eorl_lab.api import metrics as metrics_api


def _run_level_metric_json(run_name: str, metric_name: str) -> dict:
	"""Reads a run-level EORL Metric's structured (metric_json) value --
	computing and persisting it via compute_run_metrics if not already
	there, the same resolution pattern eorl_lab.api.analysis uses for
	scalar metric values."""
	# Only rows written after this run was created: a metric row under the
	# same name but older than the run belongs to a different (rolled-back)
	# run that happened to receive the same name.
	existing = frappe.db.get_value(
		"EORL Metric",
		{"run": run_name, "metric_name": metric_name, "episode": ["in", ["", None]],
			"creation": [">=", frappe.db.get_value("EORL Run", run_name, "creation")]},
		"metric_json", order_by="creation desc",
	)
	if existing is not None:
		return frappe.parse_json(existing)

	computed = metrics_api.compute_run_metrics(run_name)
	value = computed["metrics"].get(metric_name)
	if value is None or not isinstance(value, dict):
		frappe.throw(f"Metric {metric_name!r} is not available as structured JSON for run {run_name!r}.")
	return value


def _graph_to_edges(graph: dict) -> list:
	"""{from: {to: count}} -> a flat, count-sorted edge list with each
	edge's share of that FROM node's total outgoing weight -- the
	actual shape a table-based DFG/network view renders directly."""
	edges = []
	for from_node, targets in graph.items():
		total_from = sum(targets.values())
		for to_node, count in targets.items():
			edges.append(
				{
					"from": from_node, "to": to_node, "count": count,
					"pct_of_from": round(100 * count / total_from, 1) if total_from else 0,
				}
			)
	edges.sort(key=lambda e: e["count"], reverse=True)
	return edges


@frappe.whitelist()
def get_process_explorer_data(run: str, scope: str = "all_actions") -> dict:
	"""SOTA Milestone 7 (V2 section 39), extended on submission day: the
	Directly-Follows Graph, a variant table and a per-episode swimlane
	for one registered sequence view (`scope`, see
	eorl_lab.analysis.taxonomy), plus actor continuity, functional
	continuity and attribute-level path coherence side by side. All of
	it is computed from this run's events on request, so switching scope
	never needs post-processing."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	if scope not in taxonomy.SEQUENCE_SCOPES:
		frappe.throw(f"Unknown scope {scope!r}; registered scopes are {taxonomy.SEQUENCE_SCOPES}.")

	episode_events, _all_paths, outcomes, _phases = metrics_api._episode_data(run)
	episode_paths = [paths.process_path(ev, scope=scope) for ev in episode_events]
	dfg_edges = _graph_to_edges(sequence.directly_follows_graph(episode_paths))

	episodes = frappe.get_all(
		"EORL Episode", filters={"run": run}, fields=["name", "episode_number", "phase", "success", "utility"],
		order_by="episode_number asc",
	)
	swimlane = []
	for ep, events in zip(episodes, episode_events):
		steps = [
			{"actor_slot": e.organizational_function, "tool": e.action_type, "category": e.category, "choice": e.decision_value}
			for e in paths.scoped_events(events, scope)
		]
		swimlane.append({
			"episode": ep.name, "episode_number": ep.episode_number, "phase": ep.phase, "success": ep.success,
			"utility": ep.utility, "steps": steps,
		})

	variant_counts = {}
	for path in episode_paths:
		variant_counts[tuple(path)] = variant_counts.get(tuple(path), 0) + 1
	variants = [
		{"variant": i + 1, "episodes": count, "share": count / len(episode_paths), "length": len(path), "path": list(path)}
		for i, (path, count) in enumerate(sorted(variant_counts.items(), key=lambda kv: -kv[1]))
	]

	all_events = [e for ev in episode_events for e in ev]
	return {
		"run": run, "scope": scope, "taxonomy_version": taxonomy.TAXONOMY_VERSION,
		"dfg_edges": dfg_edges, "swimlane": swimlane, "variants": variants,
		"summary": {
			"episodes": len(episode_paths),
			"unique_sequence_count": sequence.unique_sequence_count(episode_paths),
			"sequence_entropy": sequence.sequence_entropy(episode_paths),
			"modal_path_share": sequence.modal_path_share(episode_paths),
		},
		"continuity": {
			"actor_continuity": coherence.actor_continuity(all_events),
			"functional_continuity": coherence.functional_continuity(all_events),
			"path_coherence_v1": attribute_coherence.attribute_coherence(all_events, scope=scope),
			"path_coherence_version": attribute_coherence.PATH_COHERENCE_VERSION,
		},
	}


@frappe.whitelist()
def get_network_explorer_data(run: str) -> dict:
	"""SOTA Milestone 7 (V2 section 42, scoped to the edge-weighted
	communication network already computed in Milestone 7's metric
	suite -- centrality/density and other graph-theoretic measures
	remain future work, not built speculatively here)."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	edges = _graph_to_edges(_run_level_metric_json(run, "communication_network"))
	actors = sorted({e["from"] for e in edges} | {e["to"] for e in edges})
	return {"run": run, "actors": actors, "edges": edges}


@frappe.whitelist()
def get_adaptation_view_data(run: str) -> dict:
	"""SOTA Milestone 7 (V2 section 40), extended on submission day: one
	point per episode (phase, success, utility, chosen supplier, whether
	the episode's consequential path was viable, and whether that path
	was already in the pre-shock repertoire), the regime shift's trigger
	episode, and the repertoire and shock-adaptation summaries. The three
	repertoire sets (observed, viable, activated after the shock) are
	reported separately so variation is not mistaken for repertoire."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	episodes = frappe.get_all(
		"EORL Episode", filters={"run": run}, fields=["name", "episode_number", "phase", "success"],
		order_by="episode_number asc",
	)
	run_doc = frappe.get_doc("EORL Run", run)
	regime_shift_snapshot = frappe.parse_json(run_doc.regime_shift_snapshot_json or "null")
	trigger_episode = regime_shift_snapshot.get("trigger_episode") if regime_shift_snapshot else None

	episode_events, _paths, outcomes, phases = metrics_api._episode_data(run)
	consequential = [paths.process_path(ev, scope="consequential_actions") for ev in episode_events]
	chosen = [metrics_api._chosen_counterparty(ev) for ev in episode_events]
	pre_viable = {
		tuple(p) for p, o, ph in zip(consequential, outcomes, phases) if ph in ("warmup", "stable") and repertoire.is_viable_v2(o)
	}

	points = []
	for e, path, outcome, party in zip(episodes, consequential, outcomes, chosen):
		points.append({
			"episode": e.name, "episode_number": e.episode_number, "phase": e.phase, "success": e.success,
			"utility": repertoire.episode_utility(outcome), "chosen_supplier": party,
			"viable": repertoire.is_viable_v2(outcome), "in_pre_shock_repertoire": tuple(path) in pre_viable,
		})

	return {
		"run": run,
		"episodes": points,
		"regime_shift_trigger_episode": trigger_episode,
		"repertoire": repertoire.adaptive_repertoire(consequential, outcomes, phases),
		"shock_adaptation": adaptation.shock_adaptation(consequential, outcomes, phases, chosen),
	}


@frappe.whitelist()
def get_survival_analysis_data(run_ids, threshold_fraction: float = 0.9) -> dict:
	"""SOTA Milestone 9 (V2 section 44.4: "Time to recovery / completion
	-> Kaplan-Meier visualization"). For each run, computes
	episodes_to_recover (eorl_lab.analysis.recovery) from its own real
	post-shock performance -- a run that never recovers within its
	observed episodes becomes a right-censored observation at its own
	last post-shock episode, not a dropped data point; a run with no
	regime shift at all (no post-shock episodes to measure recovery
	over) is skipped rather than silently counted as instant
	recovery."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	if isinstance(run_ids, str):
		run_ids = frappe.parse_json(run_ids)

	durations, events, details = [], [], []
	for run_name in run_ids:
		_episode_events, _episode_paths, outcomes, phases = metrics_api._episode_data(run_name)
		post_count = sum(1 for ph in phases if ph in recovery.POST_PHASES)
		if post_count == 0:
			continue
		performance = [repertoire.episode_utility(o) for o in outcomes]
		recovered_at = recovery.episodes_to_recover(performance, phases, float(threshold_fraction))
		if recovered_at is not None:
			duration, event_observed = recovered_at, 1
		else:
			duration, event_observed = post_count - 1, 0
		durations.append(duration)
		events.append(event_observed)
		details.append({"run": run_name, "duration": duration, "event_observed": event_observed})

	if len(durations) < 2:
		frappe.throw(
			"Need at least 2 runs with post-shock episodes (i.e. launched with a regime shift) "
			"for a survival analysis."
		)

	result = stats.kaplan_meier_recovery(durations, events)
	result["runs"] = details
	return result
