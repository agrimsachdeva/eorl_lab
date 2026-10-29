import frappe


@frappe.whitelist()
def list_episodes(run: str) -> list:
	return frappe.get_all(
		"EORL Episode",
		filters={"run": run},
		fields=["name", "episode_number", "phase", "status", "success", "scenario_case_id"],
		order_by="episode_number asc",
	)


@frappe.whitelist()
def get_episode_trace(episode: str) -> dict:
	"""Backs the Trace Explorer (spec section 7.7): a chronological
	reconstruction of one episode from raw EORL Event rows -- the same
	rows Milestones 2-5 have been writing all along, just read back in
	order."""
	ep = frappe.get_doc("EORL Episode", episode)
	events = frappe.get_all(
		"EORL Event",
		filters={"episode": episode},
		fields=[
			"name", "sequence_no", "event_type", "actor_slot", "actor_instance_id",
			"target_type", "target_id", "success", "payload_json", "wallclock_timestamp",
			"trace_id", "correlation_id",
		],
		order_by="sequence_no asc",
	)
	return {"episode": ep.as_dict(), "events": events}
