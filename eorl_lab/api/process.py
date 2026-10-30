import frappe

from eorl_lab.api import metrics as metrics_api


def _run_level_metric_json(run_name: str, metric_name: str) -> dict:
	"""Reads a run-level EORL Metric's structured (metric_json) value --
	computing and persisting it via compute_run_metrics if not already
	there, the same resolution pattern eorl_lab.api.analysis uses for
	scalar metric values."""
	existing = frappe.db.get_value(
		"EORL Metric",
		{"run": run_name, "metric_name": metric_name, "episode": ["in", ["", None]]},
		"metric_json",
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
def get_process_explorer_data(run: str) -> dict:
	"""SOTA Milestone 7 (V2 section 39, scoped to the DFG + episode
	swimlane slice): the Directly-Follows Graph as a count-sorted edge
	list (built from the already-computed, pooled-across-episodes
	`directly_follows_graph` EORL Metric -- Milestone 7's own process-
	mining primitive, not recomputed here), plus a per-episode swimlane
	of (actor, tool) steps built directly from this run's raw event
	trace."""
	dfg_edges = _graph_to_edges(_run_level_metric_json(run, "directly_follows_graph"))

	episodes = frappe.get_all(
		"EORL Episode", filters={"run": run}, fields=["name", "episode_number", "phase", "success"],
		order_by="episode_number asc",
	)
	tool_events = frappe.get_all(
		"EORL Event", filters={"run": run, "event_type": "tool_result"},
		fields=["episode", "sequence_no", "actor_slot", "target_id"], order_by="sequence_no asc",
	)
	steps_by_episode: dict = {}
	for event in tool_events:
		steps_by_episode.setdefault(event.episode, []).append(
			{"actor_slot": event.actor_slot, "tool": event.target_id}
		)

	swimlane = [
		{
			"episode": ep.name, "episode_number": ep.episode_number, "phase": ep.phase, "success": ep.success,
			"steps": steps_by_episode.get(ep.name, []),
		}
		for ep in episodes
	]

	return {"run": run, "dfg_edges": dfg_edges, "swimlane": swimlane}


@frappe.whitelist()
def get_network_explorer_data(run: str) -> dict:
	"""SOTA Milestone 7 (V2 section 42, scoped to the edge-weighted
	communication network already computed in Milestone 7's metric
	suite -- centrality/density and other graph-theoretic measures
	remain future work, not built speculatively here)."""
	edges = _graph_to_edges(_run_level_metric_json(run, "communication_network"))
	actors = sorted({e["from"] for e in edges} | {e["to"] for e in edges})
	return {"run": run, "actors": actors, "edges": edges}


@frappe.whitelist()
def get_adaptation_view_data(run: str) -> dict:
	"""SOTA Milestone 7 (V2 section 40, scoped to the per-episode
	performance trajectory the Scientific Cockpit's KPI cards summarize
	but don't visualize): one point per episode (episode_number, phase,
	success), plus the regime shift's trigger_episode if this run was
	launched with one, so the front end can mark the shock point on a
	trajectory chart rather than the caller having to infer it."""
	episodes = frappe.get_all(
		"EORL Episode", filters={"run": run}, fields=["episode_number", "phase", "success"],
		order_by="episode_number asc",
	)
	run_doc = frappe.get_doc("EORL Run", run)
	regime_shift_snapshot = frappe.parse_json(run_doc.regime_shift_snapshot_json or "null")
	trigger_episode = regime_shift_snapshot.get("trigger_episode") if regime_shift_snapshot else None

	return {
		"run": run,
		"episodes": [{"episode_number": e.episode_number, "phase": e.phase, "success": e.success} for e in episodes],
		"regime_shift_trigger_episode": trigger_episode,
	}
