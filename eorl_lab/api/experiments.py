import frappe

from eorl_lab.runtime.orchestrator import run_architecture


@frappe.whitelist()
def get_experiment_summary(experiment_name: str) -> dict:
	exp = frappe.get_doc("EORL Experiment", experiment_name)
	return {
		"experiment": exp.name,
		"status": exp.status,
		"architecture_a": exp.architecture_a,
		"architecture_b": exp.architecture_b,
		"factors": [
			{"factor_name": r.factor_name, "level_label": r.level_label, "factor_type": r.factor_type, "is_baseline": r.is_baseline}
			for r in exp.factors
		],
		"cell_count": exp.cell_count(),
		"repetitions_per_cell": exp.repetitions_per_cell,
		"total_run_count": exp.total_run_count(),
		"episode_count": exp.episode_count,
		"seed_strategy": exp.seed_strategy,
		"base_seed": exp.base_seed,
		"regime_shift": exp.regime_shift,
		"focal_construct": exp.focal_construct,
	}


@frappe.whitelist()
def validate_experiment(experiment_name: str) -> dict:
	exp = frappe.get_doc("EORL Experiment", experiment_name)
	errors = []
	cells = exp.factorial_cells()

	if cells:
		# SOTA Milestone 4: the generalized N-factor path. Every row's
		# referenced document must actually exist, and at least one
		# factor must resolve an architecture for every cell (either its
		# own 'architecture' factor, or the architecture_a fallback).
		for row in exp.factors:
			if row.factor_type == "architecture" and row.architecture and not frappe.db.exists("EORL Architecture", row.architecture):
				errors.append(f"factor {row.factor_name!r} level {row.level_label!r}: architecture {row.architecture!r} does not exist")
			if row.factor_type == "regime_shift" and row.regime_shift and not frappe.db.exists("EORL Regime Shift", row.regime_shift):
				errors.append(f"factor {row.factor_name!r} level {row.level_label!r}: regime_shift {row.regime_shift!r} does not exist")
		has_architecture_factor = any(row.factor_type == "architecture" for row in exp.factors)
		if not has_architecture_factor and not exp.architecture_a:
			errors.append("no 'architecture' factor is defined and architecture_a is not set as a fallback")
	else:
		# Original Milestone 6 path, unchanged.
		if not exp.architecture_a:
			errors.append("architecture_a is required")
		if exp.architecture_b and not frappe.db.exists("EORL Architecture", exp.architecture_b):
			errors.append(f"architecture_b {exp.architecture_b!r} does not exist")

	if exp.regime_shift and not frappe.db.exists("EORL Regime Shift", exp.regime_shift):
		errors.append(f"regime_shift {exp.regime_shift!r} does not exist")
	if exp.focal_construct and not frappe.db.exists("EORL Construct", exp.focal_construct):
		errors.append(f"focal_construct {exp.focal_construct!r} does not exist")

	return {"valid": not errors, "errors": errors, "cell_count": exp.cell_count(), "total_run_count": exp.total_run_count()}


def _resolve_cell(exp, cell: dict) -> tuple:
	"""Resolves one factorial cell (a {factor_name: EORL Experiment
	Factor row} dict) into the (architecture, regime_shift) pair
	run_architecture() actually needs, falling back to the experiment's
	own architecture_a / regime_shift for any dimension this cell
	doesn't itself factor over."""
	architecture = None
	regime_shift_set = False
	regime_shift = None
	for row in cell.values():
		if row.factor_type == "architecture":
			architecture = row.architecture
		elif row.factor_type == "regime_shift":
			regime_shift = row.regime_shift
			regime_shift_set = True
	architecture = architecture or exp.architecture_a
	if not regime_shift_set:
		regime_shift = exp.regime_shift
	return architecture, regime_shift


@frappe.whitelist()
def launch_pilot(experiment_name: str, repetitions: int = None) -> dict:
	"""Milestone 6 deviation: runs synchronously within the request for a
	small pilot (spec section 7.5's "Launch Pilot"), not queued as
	background jobs. Queued/external execution for full-scale experiments
	is Milestone 9's scope.

	SOTA Milestone 4 (V2 section 28.7) generalizes this from the fixed
	architecture_a/architecture_b pair to the full cartesian product of
	`EORL Experiment.factors`' levels when any are defined --
	`seed_strategy == "paired"` still gives every cell in the same
	repetition the identical exogenous scenario stream (spec section 18);
	"independent" offsets by cell index so they don't collide but also
	aren't required to match. When `factors` is empty, behavior is
	byte-identical to the original architecture_a-vs-architecture_b path."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])

	exp = frappe.get_doc("EORL Experiment", experiment_name)
	validation = validate_experiment(experiment_name)
	if not validation["valid"]:
		frappe.throw(f"Cannot launch: {'; '.join(validation['errors'])}")

	reps = int(repetitions) if repetitions else (exp.repetitions_per_cell or 1)
	cells = exp.factorial_cells()

	launched = []
	if cells:
		for rep in range(reps):
			for cell_index, cell in enumerate(cells):
				if exp.seed_strategy == "independent":
					seed = (exp.base_seed or 42) + rep * 1000 + cell_index * 100
				else:
					seed = (exp.base_seed or 42) + rep

				architecture, regime_shift = _resolve_cell(exp, cell)
				if not architecture:
					frappe.throw(
						f"Cell {cell_index} ({ {n: r.level_label for n, r in cell.items()} }) has no "
						f"architecture resolved (no 'architecture' factor in it and no architecture_a fallback)."
					)

				cell_label = ",".join(f"{n}={r.level_label}" for n, r in cell.items())
				result = run_architecture(
					architecture, seed=seed, episode_count=exp.episode_count or 1, regime_shift=regime_shift,
					actor_engine=exp.get("actor_engine"), experiment=exp.name, cell_id=f"{cell_label}|rep{rep}",
				)
				launched.append(
					{
						"cell": {name: row.level_label for name, row in cell.items()},
						"architecture": architecture,
						"regime_shift": regime_shift,
						"repetition": rep,
						"seed": seed,
						"run": result["run"],
						"success": result["outcome"]["success"],
						"event_count": result["event_count"],
					}
				)
	else:
		architectures = [a for a in [exp.architecture_a, exp.architecture_b] if a]
		for rep in range(reps):
			for arch_index, architecture in enumerate(architectures):
				if exp.seed_strategy == "independent":
					seed = (exp.base_seed or 42) + rep * 1000 + arch_index * 100
				else:
					seed = (exp.base_seed or 42) + rep

				result = run_architecture(
					architecture,
					seed=seed,
					episode_count=exp.episode_count or 1,
					regime_shift=exp.regime_shift,
					actor_engine=exp.get("actor_engine"),
					experiment=exp.name,
					cell_id=f"{architecture}|rep{rep}",
				)
				launched.append(
					{
						"architecture": architecture,
						"repetition": rep,
						"seed": seed,
						"run": result["run"],
						"success": result["outcome"]["success"],
						"event_count": result["event_count"],
					}
				)

	exp.status = "pilot_launched"
	exp.save()

	return {"experiment": exp.name, "runs": launched}


@frappe.whitelist()
def compile_theory(
	focal_construct: str = None,
	theoretical_definition: str = "",
	proposed_mechanism: str = "",
	manipulation: str = "",
	counterfactual_condition: str = "",
	outcomes: str = "",
	mediating_measures: str = "",
	boundary_conditions: str = "",
	experiment_name: str = None,
) -> dict:
	"""SOTA Milestone 10 (V2 section 21, "Theory-to-experiment workflow /
	Theory Compiler"): a STRUCTURED WIZARD -- the spec's own words are
	"do not attempt fully autonomous theory generation" -- that takes
	the 8 researcher inputs section 21 names and scaffolds a real
	`EORL Experiment` + `EORL Analysis Plan` from them, pre-filled with
	everything that can be honestly derived from structured input
	alone. It does NOT invent an architecture, a scenario, or a metric
	the researcher didn't effectively name: `outcome_metric` is only
	auto-filled when `focal_construct` resolves to an `EORL Construct`
	that already has a real `measurement_function` (today, only
	"Routine coherence" and "Adaptive repertoire" qualify); every other
	construct leaves it as an explicit, visible placeholder rather than
	guessing. The researcher still has to set `architecture_a` (and
	`outcome_metric`, if left as the placeholder) before launching --
	same as any other `EORL Experiment`."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])

	if not experiment_name:
		experiment_name = f"Theory: {(theoretical_definition or focal_construct or 'Untitled')[:80]}"
	if frappe.db.exists("EORL Experiment", experiment_name):
		frappe.throw(f"An EORL Experiment named {experiment_name!r} already exists -- pick a different name.")

	outcome_metric = None
	if focal_construct and frappe.db.exists("EORL Construct", focal_construct):
		construct = frappe.get_doc("EORL Construct", focal_construct)
		if construct.measurement_function:
			outcome_metric = construct.measurement_function.rsplit(".", 1)[-1]
	outcome_metric_was_guessed = bool(outcome_metric)
	if not outcome_metric:
		outcome_metric = "UNSET -- choose a real eorl_lab.api.metrics.compute_run_metrics metric name"

	notes_parts = []
	if mediating_measures:
		notes_parts.append(f"Mediating process measures: {mediating_measures}")
	if boundary_conditions:
		notes_parts.append(f"Boundary conditions: {boundary_conditions}")

	experiment = frappe.get_doc(
		{
			"doctype": "EORL Experiment",
			"experiment_name": experiment_name,
			"status": "draft",
			"research_question": theoretical_definition,
			"theoretical_mechanism": proposed_mechanism,
			"focal_construct": focal_construct,
			"primary_outcomes": outcomes,
			"notes": "\n".join(notes_parts),
		}
	).insert(ignore_permissions=True)

	plan_name = f"{experiment_name} - Analysis Plan"
	if frappe.db.exists("EORL Analysis Plan", plan_name):
		plan_name = f"{plan_name} {frappe.generate_hash(length=4)}"
	plan = frappe.get_doc(
		{
			"doctype": "EORL Analysis Plan",
			"plan_name": plan_name,
			"experiment": experiment.name,
			"research_question": theoretical_definition,
			"estimand": counterfactual_condition,
			"outcome_metric": outcome_metric,
			"contrast": manipulation,
			"analysis_unit": "run",
		}
	).insert(ignore_permissions=True)

	next_steps = ["Set architecture_a (and optionally architecture_b or factors) on the Experiment."]
	next_steps.append(
		"outcome_metric was auto-filled from the focal construct's measurement_function."
		if outcome_metric_was_guessed
		else "outcome_metric is an explicit placeholder -- set a real metric name on the Analysis Plan before launching."
	)
	next_steps.append("Launch via eorl_lab.api.experiments.launch_pilot once the Experiment's design is complete.")

	return {
		"experiment": experiment.name, "analysis_plan": plan.name,
		"outcome_metric_guessed": outcome_metric_was_guessed, "next_steps": next_steps,
	}


@frappe.whitelist()
def estimate_experiment_cost(experiment_name: str) -> dict:
	"""Submission-day plan section 23: expected model calls, tokens and
	wallclock time for an experiment's full design, from the per-episode
	averages of completed runs of the same architectures. Architectures
	with no completed run yet are reported as having no basis rather
	than guessed."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	exp = frappe.get_doc("EORL Experiment", experiment_name)
	reps = exp.repetitions_per_cell or 1
	episodes = exp.episode_count or 1
	cells = exp.factorial_cells()
	if cells:
		architectures = [_resolve_cell(exp, cell)[0] for cell in cells]
	else:
		architectures = [a for a in [exp.architecture_a, exp.architecture_b] if a]

	per_arch, totals = [], {"model_calls": 0.0, "total_tokens": 0.0, "wallclock_seconds": 0.0}
	for architecture in architectures:
		runs = frappe.db.sql(
			"""select name, model_calls, total_tokens, wallclock_seconds, current_episode from `tabEORL Run`
			where status='completed' and wallclock_seconds > 0 and current_episode > 0
			and architecture_snapshot_json like %s""",
			(f'%"name": "{architecture}"%',), as_dict=True,
		)
		if not runs:
			per_arch.append({"architecture": architecture, "basis_runs": 0})
			continue
		n_ep = sum(r.current_episode for r in runs)
		rate = {k: sum((r.get(k) or 0) for r in runs) / n_ep for k in totals}
		projected = {k: v * episodes * reps for k, v in rate.items()}
		for k in totals:
			totals[k] += projected[k]
		per_arch.append({"architecture": architecture, "basis_runs": len(runs), "per_episode": rate, "projected": projected})
	return {
		"experiment": exp.name, "runs_planned": len(architectures) * reps, "episodes_per_run": episodes,
		"by_architecture": per_arch, "projected_total": totals,
		"projected_hours": totals["wallclock_seconds"] / 3600.0,
	}
