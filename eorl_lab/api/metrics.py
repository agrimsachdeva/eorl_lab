import frappe


@frappe.whitelist()
def compare_runs(runs) -> list:
	"""Backs the Compare Runs page (spec section 7.8). Milestone 6
	deviation: returns simple raw aggregates (episode/event counts,
	success rate, distinct-actor count) read directly off EORL
	Episode/Event, not the process-path/coherence/repertoire/entropy
	metrics of spec section 17 -- those need the process-path extraction
	layer, which is Milestone 7."""
	if isinstance(runs, str):
		runs = frappe.parse_json(runs)

	comparison = []
	for run_name in runs:
		run_doc = frappe.get_doc("EORL Run", run_name)
		episodes = frappe.get_all("EORL Episode", filters={"run": run_name}, fields=["success"])
		actor_rows = frappe.get_all("EORL Event", filters={"run": run_name}, fields=["actor_slot"])
		distinct_actors = {row.actor_slot for row in actor_rows if row.actor_slot}

		comparison.append(
			{
				"run": run_name,
				"status": run_doc.status,
				"run_seed": run_doc.run_seed,
				"episode_count": len(episodes),
				"success_rate": (sum(1 for e in episodes if e.success) / len(episodes)) if episodes else None,
				"distinct_actor_count": len(distinct_actors),
				"actor_slots": sorted(distinct_actors),
				"event_count": run_doc.event_count,
			}
		)
	return comparison
