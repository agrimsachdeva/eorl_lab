import csv
import io
import math

import scipy
import frappe

from eorl_lab.analysis import stats
from eorl_lab.api import metrics as metrics_api


def _clean_float(value):
	"""NaN/Inf are legitimate outputs of a degenerate comparison (e.g.
	zero variance in both groups -- Welch's t-statistic is then 0/0)
	but MySQL rejects them outright for a Float column. NULL is also
	the scientifically correct representation here: 'undefined', not
	some fabricated number."""
	if value is None:
		return None
	if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
		return None
	return value


def _run_level_metric(run_name: str, metric_name: str) -> float:
	"""Resolves ONE value per run for `metric_name` -- the independence
	guardrail's unit of analysis (V2 section 44.2). Reads the persisted
	run-level `EORL Metric` row if one already exists; computes and
	persists it via compute_run_metrics otherwise. Never reads a
	per-episode value for this purpose."""
	existing = frappe.db.get_value(
		"EORL Metric",
		{"run": run_name, "metric_name": metric_name, "episode": ["in", ["", None]]},
		"metric_value",
	)
	if existing is not None:
		return existing

	computed = metrics_api.compute_run_metrics(run_name)
	value = computed["metrics"].get(metric_name)
	if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
		frappe.throw(
			f"Metric {metric_name!r} is not available as a single numeric run-level value for "
			f"run {run_name!r} -- check EORL Analysis Plan.outcome_metric names a real metric "
			f"from eorl_lab.api.metrics.compute_run_metrics's output."
		)
	return value


_EPISODE_LEVEL_METRICS = {"success_rate"}


def _episode_level_outcome(run_name: str, metric_name: str) -> list:
	"""SOTA Milestone 6: the ONE metric with an unambiguous, already
	-stored per-episode value -- EORL Episode.success (0/1) IS the
	episode-level counterpart of the run-level 'success_rate' metric.
	Every other metric this app computes (sequence_entropy,
	actor_continuity, ...) is a genuine run-level aggregate over an
	entire run's episode paths and has no single-episode definition --
	so episode-level, mixed-effects analysis is honestly limited to
	outcome_metric='success_rate' for now, rather than pretending a
	per-episode value exists for metrics that don't have one."""
	if metric_name not in _EPISODE_LEVEL_METRICS:
		frappe.throw(
			f"outcome_metric={metric_name!r} has no per-episode definition -- episode-level "
			f"(mixed_effects) analysis is only supported for: {sorted(_EPISODE_LEVEL_METRICS)}."
		)
	episodes = frappe.get_all(
		"EORL Episode", filters={"run": run_name}, fields=["success"], order_by="episode_number asc"
	)
	return [1.0 if e.success else 0.0 for e in episodes]


def _episode_count(run_name: str) -> int:
	return frappe.db.count("EORL Episode", {"run": run_name})


def _branch_lineage_key(run_name: str):
	"""(parent_run, branch_point_episode) for a run, or None if it is
	not itself a branch (SOTA Milestone 2)."""
	parent_run, branch_point_episode = frappe.db.get_value(
		"EORL Run", run_name, ["parent_run", "branch_point_episode"]
	)
	if not parent_run:
		return None
	return (parent_run, branch_point_episode)


def _verify_sibling_branches(group_a: list, group_b: list):
	"""V2 section 44.3: 'If two branches share identical history until
	episode t, treat them as paired/matched... Do not treat the
	branches as unrelated independent histories.' The inverse also
	holds here: refuse to treat runs as paired just because the
	researcher's EORL Analysis Plan.paired_by says so -- verify every
	pair actually IS a sibling branch pair first."""
	if len(group_a) != len(group_b):
		frappe.throw(
			f"paired_by requires equal-length, position-matched groups (got {len(group_a)} vs {len(group_b)})."
		)
	for run_a, run_b in zip(group_a, group_b):
		key_a, key_b = _branch_lineage_key(run_a), _branch_lineage_key(run_b)
		if key_a is None or key_b is None or key_a != key_b:
			frappe.throw(
				f"paired_by='branch_point' requires {run_a!r} and {run_b!r} to be sibling branches "
				f"of the SAME parent run at the SAME branch_point_episode (V2 section 44.3) -- got "
				f"lineage {key_a!r} vs {key_b!r}. Refusing to run a paired test on runs that aren't "
				f"actually matched."
			)


def _parse_equivalence_bounds(text):
	if not text:
		return None
	parts = [p.strip() for p in text.split(",")]
	if len(parts) != 2:
		frappe.throw(f"equivalence_bounds must be 'low,high' (got {text!r}).")
	try:
		return float(parts[0]), float(parts[1])
	except ValueError:
		frappe.throw(f"equivalence_bounds must be two numbers separated by a comma (got {text!r}).")


def _save_analysis_result(plan, result, run_ids_group_a, run_ids_group_b, n_independent_runs_a,
	n_independent_runs_b, n_episodes_a, n_episodes_b, paired, standardized_effect, mean_a, mean_b):
	ci = result.get("ci_95", (None, None))
	raw_effect = result.get(
		"mean_diff", result.get("observed_diff", result.get("observed_mean_diff", result.get("coefficient")))
	)
	doc = frappe.get_doc(
		{
			"doctype": "EORL Analysis Result",
			"analysis_plan": plan.name,
			"experiment": plan.experiment,
			"test_family": result["test"],
			"run_ids_group_a": ",".join(run_ids_group_a),
			"run_ids_group_b": ",".join(run_ids_group_b),
			"n_independent_runs_a": n_independent_runs_a,
			"n_independent_runs_b": n_independent_runs_b,
			"n_episodes_a": n_episodes_a,
			"n_episodes_b": n_episodes_b,
			"paired": 1 if paired else 0,
			"metric_definition_version": metrics_api.METRIC_VERSION,
			"stats_package_version": f"scipy {scipy.__version__}",
			"mean_a": _clean_float(mean_a),
			"mean_b": _clean_float(mean_b),
			"raw_effect": _clean_float(raw_effect),
			"standardized_effect": _clean_float(standardized_effect),
			"ci_95_lower": _clean_float(ci[0]) if ci else None,
			"ci_95_upper": _clean_float(ci[1]) if ci else None,
			"p_value": _clean_float(result["p_value"]),
			"diagnostics_json": frappe.as_json(result),
		}
	).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def compare_groups(analysis_plan_name: str, run_ids_group_a, run_ids_group_b) -> dict:
	"""SOTA Milestone 5 (V2 section 44): the only entrypoint in this app
	that runs a between-condition statistical comparison. Enforces,
	rather than merely documenting:

	- the independence guardrail (section 44.2) -- when
	  `analysis_unit == "episode"`, this now takes 54.3's SECOND branch
	  (SOTA Milestone 6): it requires `model_family == "mixed_effects"`
	  and runs a genuine two-level model with run as the random-effect
	  cluster, rather than either silently treating episodes as
	  independent OR refusing outright. `analysis_unit == "run"` still
	  takes the original independent/paired-groups path.
	- the paired-branch requirement (section 44.3) -- when
	  `paired_by` is set, VERIFIES every (group_a[i], group_b[i]) pair
	  actually is a sibling counterfactual-branch pair before running a
	  paired test, rather than trusting the caller's claim
	- "recommend, never silently select" (section 44.4) -- always
	  computes and persists BOTH the parametric and the
	  distribution-free test for whichever pairing mode applies
	- equivalence testing (section 45.1, SOTA Milestone 6): if
	  `EORL Analysis Plan.equivalence_bounds` is set, ALSO runs and
	  persists a TOST equivalence result alongside the difference tests
	- trace-linked result provenance (section 52) -- every result is a
	  real `EORL Analysis Result` row naming the exact run IDs, episode
	  counts, metric version, and statistics package version that
	  produced it
	"""
	if isinstance(run_ids_group_a, str):
		run_ids_group_a = frappe.parse_json(run_ids_group_a)
	if isinstance(run_ids_group_b, str):
		run_ids_group_b = frappe.parse_json(run_ids_group_b)

	plan = frappe.get_doc("EORL Analysis Plan", analysis_plan_name)

	if plan.analysis_unit == "episode":
		return _compare_groups_episode_level_mixed_effects(plan, run_ids_group_a, run_ids_group_b)
	if plan.analysis_unit != "run":
		frappe.throw(f"Unknown analysis_unit: {plan.analysis_unit!r} (must be 'run' or 'episode').")

	if len(run_ids_group_a) < 2 or len(run_ids_group_b) < 2:
		frappe.throw("Each group needs at least 2 independent runs for this comparison.")

	values_a = [_run_level_metric(r, plan.outcome_metric) for r in run_ids_group_a]
	values_b = [_run_level_metric(r, plan.outcome_metric) for r in run_ids_group_b]
	n_episodes_a = sum(_episode_count(r) for r in run_ids_group_a)
	n_episodes_b = sum(_episode_count(r) for r in run_ids_group_b)

	paired = bool(plan.paired_by)
	permutation_iterations = plan.permutation_iterations or 10000

	if paired:
		_verify_sibling_branches(run_ids_group_a, run_ids_group_b)
		raw_results = [
			stats.paired_t_test(values_a, values_b),
			stats.paired_permutation_test(values_a, values_b, n_iterations=permutation_iterations),
		]
		standardized_effect = stats.paired_hedges_g(values_a, values_b)
	else:
		raw_results = [
			stats.welch_t_test(values_a, values_b),
			stats.permutation_test(values_a, values_b, n_iterations=permutation_iterations),
		]
		standardized_effect = stats.hedges_g(values_a, values_b)

	equivalence_bounds = _parse_equivalence_bounds(plan.equivalence_bounds)
	if equivalence_bounds:
		raw_results.append(stats.tost_equivalence(values_a, values_b, *equivalence_bounds, alpha=plan.alpha or 0.05))

	mean_a, mean_b = sum(values_a) / len(values_a), sum(values_b) / len(values_b)
	analysis_result_names = [
		_save_analysis_result(
			plan, result, run_ids_group_a, run_ids_group_b,
			len(run_ids_group_a), len(run_ids_group_b), n_episodes_a, n_episodes_b,
			paired, standardized_effect, mean_a, mean_b,
		)
		for result in raw_results
	]

	return {
		"analysis_plan": plan.name,
		"paired": paired,
		"outcome_metric": plan.outcome_metric,
		"n_independent_runs_a": len(run_ids_group_a),
		"n_independent_runs_b": len(run_ids_group_b),
		"n_episodes_a": n_episodes_a,
		"n_episodes_b": n_episodes_b,
		"mean_a": mean_a,
		"mean_b": mean_b,
		"standardized_effect": standardized_effect,
		"results": raw_results,
		"analysis_result_names": analysis_result_names,
	}


def _compare_groups_episode_level_mixed_effects(plan, run_ids_group_a: list, run_ids_group_b: list) -> dict:
	"""SOTA Milestone 6: the "explicit hierarchical specification"
	alternative V2 section 44.2 and visualization acceptance test 54.3
	ask for, once a real two-level model backs it -- episodes ARE used
	directly here, but modeled as correlated observations clustered
	within their own run (the random effect), never as independent
	rows. Requires `model_family == "mixed_effects"`: there is no other
	honest way to use `analysis_unit == "episode"` in this app yet."""
	if plan.model_family != "mixed_effects":
		frappe.throw(
			"Independence guardrail (V2 section 44.2): analysis_unit='episode' requires "
			f"model_family='mixed_effects' (got {plan.model_family!r}) -- there is no other "
			"hierarchical model built yet to honestly justify treating episodes as the analysis unit."
		)
	if len(set(run_ids_group_a)) < 2 or len(set(run_ids_group_b)) < 2:
		frappe.throw("Each group needs at least 2 distinct run clusters for a mixed-effects comparison.")

	episode_values_a, cluster_ids_a = [], []
	for run_name in run_ids_group_a:
		for value in _episode_level_outcome(run_name, plan.outcome_metric):
			episode_values_a.append(value)
			cluster_ids_a.append(run_name)

	episode_values_b, cluster_ids_b = [], []
	for run_name in run_ids_group_b:
		for value in _episode_level_outcome(run_name, plan.outcome_metric):
			episode_values_b.append(value)
			cluster_ids_b.append(run_name)

	result = stats.mixed_effects_comparison(episode_values_a, cluster_ids_a, episode_values_b, cluster_ids_b)

	mean_a = sum(episode_values_a) / len(episode_values_a)
	mean_b = sum(episode_values_b) / len(episode_values_b)
	analysis_result_name = _save_analysis_result(
		plan, result, run_ids_group_a, run_ids_group_b,
		len(set(run_ids_group_a)), len(set(run_ids_group_b)),
		len(episode_values_a), len(episode_values_b),
		False, None, mean_a, mean_b,
	)

	return {
		"analysis_plan": plan.name,
		"paired": False,
		"outcome_metric": plan.outcome_metric,
		"n_independent_runs_a": len(set(run_ids_group_a)),
		"n_independent_runs_b": len(set(run_ids_group_b)),
		"n_episodes_a": len(episode_values_a),
		"n_episodes_b": len(episode_values_b),
		"mean_a": mean_a,
		"mean_b": mean_b,
		"standardized_effect": None,
		"results": [result],
		"analysis_result_names": [analysis_result_name],
	}


@frappe.whitelist()
def export_results_table(analysis_plan_name: str, fmt: str = "markdown") -> str:
	"""SOTA Milestone 6 (V2 section 50, Results Table Generator -- scoped
	to a plain table export, not the full publication-formatting
	engine): every EORL Analysis Result for one plan, as a Markdown or
	CSV table, in the order they were computed."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	rows = frappe.get_all(
		"EORL Analysis Result",
		filters={"analysis_plan": analysis_plan_name},
		fields=[
			"test_family", "n_independent_runs_a", "n_independent_runs_b", "n_episodes_a", "n_episodes_b",
			"paired", "mean_a", "mean_b", "raw_effect", "standardized_effect",
			"ci_95_lower", "ci_95_upper", "p_value", "stats_package_version", "creation",
		],
		order_by="creation asc",
	)
	columns = [
		"test_family", "n_independent_runs_a", "n_independent_runs_b", "n_episodes_a", "n_episodes_b",
		"paired", "mean_a", "mean_b", "raw_effect", "standardized_effect",
		"ci_95_lower", "ci_95_upper", "p_value", "stats_package_version",
	]

	if fmt == "csv":
		buffer = io.StringIO()
		writer = csv.writer(buffer)
		writer.writerow(columns)
		for row in rows:
			writer.writerow([row.get(c) for c in columns])
		return buffer.getvalue()

	header = "| " + " | ".join(columns) + " |"
	divider = "|" + "|".join(["---"] * len(columns)) + "|"
	lines = [header, divider]
	for row in rows:
		lines.append("| " + " | ".join(str(row.get(c)) for c in columns) + " |")
	return "\n".join(lines)
