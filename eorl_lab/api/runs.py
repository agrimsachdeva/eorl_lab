import frappe

from eorl_lab.observability.context import ExperimentContext
from eorl_lab.observability.events import emit_event
from eorl_lab.runtime.orchestrator import branch_run as _branch_run
from eorl_lab.runtime.orchestrator import get_full_branch_history, run_demo_episode


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


@frappe.whitelist()
def branch_run(
	source_run_name: str,
	branch_episode: int,
	additional_episode_count: int = 1,
	architecture_name: str = None,
	regime_shift: str = None,
	intervention_description: str = "",
) -> dict:
	"""SOTA Milestone 2 (V2 section 17): counterfactual branching. Clones
	actor memory accumulated through `branch_episode` and continues the
	same scenario stream under a (possibly different) architecture or
	regime shift. See eorl_lab.runtime.orchestrator.branch_run for the
	full honest-scope caveats (ERP state itself is not forked)."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	return _branch_run(
		source_run_name,
		int(branch_episode),
		additional_episode_count=int(additional_episode_count),
		architecture_name=architecture_name,
		regime_shift=regime_shift,
		intervention_description=intervention_description,
	)


@frappe.whitelist()
def get_branch_history(run: str) -> list:
	"""Reconstructs one continuous episode history for `run` across its
	full branch lineage (spec section 17's acceptance test: two branches
	must share byte-equivalent history through their common branch
	point)."""
	return get_full_branch_history(run)


@frappe.whitelist()
def mark_ablation(run: str, baseline_run: str, mechanism: str) -> dict:
	"""SOTA Milestone 4 (V2 section 19): "Provide an interface for
	marking a run as an ablation of another configuration." A thin,
	explicit marking, recorded after the fact -- this does not itself
	configure or toggle any mechanism (that's done the normal way, via
	whatever EORL Tool Policy / EORL Memory Profile / EORL Communication
	Policy fields the researcher already varied to produce `run`); it
	just records that `run` represents `baseline_run` with `mechanism`
	ablated, for the Mechanism/Ablation Dashboard (a later milestone) to
	consume. Independent of branch_run()'s shared-history lineage: an
	ablation need not share any episodes with its baseline."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	if not frappe.db.exists("EORL Run", baseline_run):
		frappe.throw(f"Unknown baseline run: {baseline_run}")
	if run == baseline_run:
		frappe.throw("A run cannot be marked as an ablation of itself.")

	run_doc = frappe.get_doc("EORL Run", run)
	run_doc.is_ablation_of = baseline_run
	run_doc.ablation_mechanism = mechanism
	run_doc.save(ignore_permissions=True)

	ctx = ExperimentContext(run_id=run_doc.name)
	emit_event(ctx, "run_marked_ablation", payload={"baseline_run": baseline_run, "mechanism": mechanism})

	return {"run": run_doc.name, "is_ablation_of": baseline_run, "ablation_mechanism": mechanism}
