import frappe

from eorl_lab.observability.exporter import build_full_bundle_zip
from eorl_lab.observability.replay import reproduce_run as _reproduce_run


@frappe.whitelist()
def export_run_bundle(run: str) -> dict:
	"""Milestone 6's raw-data JSON export, kept for the Reproducibility
	page's lightweight "quick export" option. download_full_bundle below
	is the Milestone 8 artifact spec section 7.9 actually asks for."""
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


@frappe.whitelist(allow_guest=False)
def download_full_bundle(run: str):
	"""Streams the full spec section 7.9 reproducibility bundle (zip) as
	a native browser download -- not a JSON blob over the RPC channel,
	since the bundle includes a full event log and can be large."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	zip_bytes = build_full_bundle_zip(run)
	frappe.local.response.filename = f"{run}_reproducibility_bundle.zip"
	frappe.local.response.filecontent = zip_bytes
	frappe.local.response.type = "download"


@frappe.whitelist()
def reproduce_run(run_name: str) -> dict:
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	return _reproduce_run(run_name)
