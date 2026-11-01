"""Queued execution (submission-day plan section 24). A launch creates
the EORL Run row immediately with status "queued" and hands the work to
a Frappe background worker, so the browser request returns at once and
the researcher can launch several runs and leave the page. Requires a
running `bench worker` for the "long" queue."""
import frappe
from frappe.utils import now_datetime

from eorl_lab.api.experiments import _resolve_cell

WRITE_ROLES = ["System Manager", "EORL Administrator", "EORL Researcher"]
JOB_TIMEOUT_SECONDS = 6 * 3600


def _enqueue(architecture: str, seed: int, episode_count: int, regime_shift=None, actor_engine=None,
	experiment=None, cell_id=None, now: bool = False) -> str:
	run = frappe.get_doc({
		"doctype": "EORL Run", "run_seed": seed, "status": "queued", "experiment": experiment, "cell_id": cell_id,
		"frappe_version": frappe.__version__,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.enqueue(
		"eorl_lab.runtime.orchestrator.run_queued", queue="long", timeout=JOB_TIMEOUT_SECONDS, now=now,
		job_name=f"eorl-run-{run.name}",
		run_name=run.name, architecture_name=architecture, seed=int(seed), episode_count=int(episode_count),
		regime_shift=regime_shift or None, actor_engine=actor_engine or None, experiment=experiment, cell_id=cell_id,
	)
	return run.name


@frappe.whitelist()
def enqueue_run(architecture_name: str, seed: int = 42, episode_count: int = 1, regime_shift: str = None, actor_engine: str = None) -> dict:
	frappe.only_for(WRITE_ROLES)
	return {"run": _enqueue(architecture_name, int(seed), int(episode_count), regime_shift, actor_engine), "status": "queued"}


@frappe.whitelist()
def enqueue_experiment(experiment_name: str, repetitions: int = None) -> dict:
	"""Queues every run of an experiment's design: the same cells and
	seeds launch_pilot would run synchronously."""
	frappe.only_for(WRITE_ROLES)
	from eorl_lab.api.experiments import validate_experiment

	exp = frappe.get_doc("EORL Experiment", experiment_name)
	validation = validate_experiment(experiment_name)
	if not validation["valid"]:
		frappe.throw(f"Cannot queue: {'; '.join(validation['errors'])}")
	reps = int(repetitions) if repetitions else (exp.repetitions_per_cell or 1)
	cells = exp.factorial_cells() or [None]
	queued = []
	for rep in range(reps):
		for cell_index, cell in enumerate(cells):
			if cell is None:
				architectures = [a for a in [exp.architecture_a, exp.architecture_b] if a]
				for arch_index, architecture in enumerate(architectures):
					seed = (exp.base_seed or 42) + (rep * 1000 + arch_index * 100 if exp.seed_strategy == "independent" else rep)
					queued.append(_enqueue(architecture, seed, exp.episode_count or 1, exp.regime_shift, exp.get("actor_engine"),
						experiment=exp.name, cell_id=f"{architecture}|rep{rep}"))
				continue
			seed = (exp.base_seed or 42) + (rep * 1000 + cell_index * 100 if exp.seed_strategy == "independent" else rep)
			architecture, regime_shift = _resolve_cell(exp, cell)
			label = ",".join(f"{n}={r.level_label}" for n, r in cell.items())
			queued.append(_enqueue(architecture, seed, exp.episode_count or 1, regime_shift, exp.get("actor_engine"),
				experiment=exp.name, cell_id=f"{label}|rep{rep}"))
	return {"experiment": exp.name, "queued_runs": queued}


@frappe.whitelist()
def cancel_run(run: str) -> dict:
	"""A queued run is cancelled at once. A running run stops before its
	next episode, and the episodes it already finished are kept."""
	frappe.only_for(WRITE_ROLES)
	status = frappe.db.get_value("EORL Run", run, "status")
	if status not in ("queued", "running", "initializing"):
		frappe.throw(f"{run} is {status}; only queued or running runs can be cancelled.")
	frappe.cache().set_value(f"eorl_cancel:{run}", 1, expires_in_sec=7 * 24 * 3600)
	if status == "queued":
		frappe.db.set_value("EORL Run", run, {"status": "cancelled", "ended_at": now_datetime()})
	return {"run": run, "previous_status": status, "cancel_requested": True}


@frappe.whitelist()
def list_queue(limit: int = 50) -> list:
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	return frappe.get_all(
		"EORL Run", filters={"status": ["in", ["queued", "running", "initializing", "cancelled", "failed", "completed"]]},
		fields=["name", "status", "experiment", "cell_id", "run_seed", "current_episode", "failure_type", "creation", "ended_at"],
		order_by="creation desc", limit_page_length=int(limit),
	)
