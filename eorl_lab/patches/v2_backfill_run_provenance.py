import frappe

from eorl_lab.providers.factory import engine_type_of


def execute():
	"""Fills EORL Run.actor_engine and routine_template for runs recorded
	before those fields existed. The model profile each slot was bound to
	comes from the run's own frozen agent snapshot; that profile's
	provider is read as it is today, since older snapshots did not copy
	it. Every such run used procure-to-pay. Nothing else about the run is
	touched."""
	runs = frappe.get_all("EORL Run", filters={"actor_engine": ["in", ["", None]]}, fields=["name", "agent_snapshots_json"])
	for run in runs:
		snapshots = frappe.parse_json(run.agent_snapshots_json or "{}") or {}
		engines = set()
		for snap in snapshots.values():
			profile = (snap or {}).get("model_profile")
			provider = frappe.db.get_value("EORL Model Profile", profile, "provider") if profile else None
			engines.add(engine_type_of(provider) if provider else "unknown")
		engine = engines.pop() if len(engines) == 1 else ("mixed" if engines else None)
		values = {"routine_template": "Procure-to-Pay"}
		if engine:
			values["actor_engine"] = engine
		frappe.db.set_value("EORL Run", run.name, values, update_modified=False)
	frappe.db.commit()
