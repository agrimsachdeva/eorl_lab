import frappe


@frappe.whitelist()
def export_run_bundle(run: str) -> dict:
	"""Backs the Reproducibility/Export page (spec section 7.9).
	Milestone 6 deviation: returns one JSON bundle (run manifest +
	episodes + full event log + memory records) for the browser to save
	as a file, not the full artifact set spec section 7.9 lists
	(resolved_prompts/, scenario_stream.jsonl, metrics.csv,
	requirements-lock.txt, README_REPRODUCE.md, etc.) or a bundle another
	process could replay -- that is the one-click reproducibility
	artifact, Milestone 8's scope. This is the raw-data half of that."""
	run_doc = frappe.get_doc("EORL Run", run)
	episodes = frappe.get_all("EORL Episode", filters={"run": run}, fields=["*"], order_by="episode_number asc")
	events = frappe.get_all("EORL Event", filters={"run": run}, fields=["*"], order_by="sequence_no asc")
	memory_records = frappe.get_all("EORL Memory Record", filters={"run": run}, fields=["*"], order_by="creation asc")

	return {
		"run_manifest": run_doc.as_dict(),
		"episodes": episodes,
		"events": events,
		"memory_records": memory_records,
		"exported_at": frappe.utils.now_datetime().isoformat(),
	}
