import frappe

from eorl_lab.runtime.orchestrator import run_demo_episode


@frappe.whitelist()
def launch_demo_episode(agent_template: str, seed: int = 42):
	"""Milestone 2 demo entrypoint, kept for its own use; the Run Monitor
	/ Experiment Studio launch flows (spec sections 7.5-7.6) go through
	eorl_lab.api.experiments.launch_pilot now."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	return run_demo_episode(agent_template, seed=int(seed))


@frappe.whitelist()
def list_runs(limit: int = 50) -> list:
	"""Backs the Run Monitor (spec section 7.6)."""
	return frappe.get_all(
		"EORL Run",
		fields=[
			"name", "status", "run_seed", "current_episode", "event_count",
			"started_at", "ended_at", "failure_reason", "creation",
		],
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def get_run_detail(run: str) -> dict:
	run_doc = frappe.get_doc("EORL Run", run)
	episodes = frappe.get_all(
		"EORL Episode",
		filters={"run": run},
		fields=["name", "episode_number", "phase", "status", "success", "scenario_case_id"],
		order_by="episode_number asc",
	)
	return {"run": run_doc.as_dict(), "episodes": episodes}
