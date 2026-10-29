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
		"cell_count": exp.cell_count(),
		"repetitions_per_cell": exp.repetitions_per_cell,
		"total_run_count": exp.total_run_count(),
		"episode_count": exp.episode_count,
		"seed_strategy": exp.seed_strategy,
		"base_seed": exp.base_seed,
		"regime_shift": exp.regime_shift,
	}


@frappe.whitelist()
def validate_experiment(experiment_name: str) -> dict:
	exp = frappe.get_doc("EORL Experiment", experiment_name)
	errors = []
	if not exp.architecture_a:
		errors.append("architecture_a is required")
	if exp.regime_shift and not frappe.db.exists("EORL Regime Shift", exp.regime_shift):
		errors.append(f"regime_shift {exp.regime_shift!r} does not exist")
	if exp.architecture_b and not frappe.db.exists("EORL Architecture", exp.architecture_b):
		errors.append(f"architecture_b {exp.architecture_b!r} does not exist")
	return {"valid": not errors, "errors": errors, "cell_count": exp.cell_count(), "total_run_count": exp.total_run_count()}


@frappe.whitelist()
def launch_pilot(experiment_name: str, repetitions: int = None) -> dict:
	"""Milestone 6 deviation: runs synchronously within the request for a
	small pilot (spec section 7.5's "Launch Pilot"), not queued as
	background jobs. Queued/external execution for full-scale experiments
	is Milestone 9's scope. `seed_strategy == "paired"` gives
	architecture_a and architecture_b the same seed per repetition (spec
	section 18); "independent" offsets by architecture index so they
	don't collide but also aren't required to match."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])

	exp = frappe.get_doc("EORL Experiment", experiment_name)
	validation = validate_experiment(experiment_name)
	if not validation["valid"]:
		frappe.throw(f"Cannot launch: {'; '.join(validation['errors'])}")

	reps = int(repetitions) if repetitions else (exp.repetitions_per_cell or 1)
	architectures = [a for a in [exp.architecture_a, exp.architecture_b] if a]

	launched = []
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
