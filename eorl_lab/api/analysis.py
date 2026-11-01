import csv
import io
import math

import scipy
import frappe

from eorl_lab.analysis import interpretation, stats, taxonomy
from eorl_lab.api import metrics as metrics_api

READ_ROLES = ["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"]

# EORL Analysis Plan.model_family -> the test_family of the result that
# counts as the plan's primary test.
_PRIMARY_TEST = {
	"welch_t": "welch_t", "permutation": "permutation", "paired_t": "paired_t",
	"paired_permutation": "paired_permutation", "mixed_effects": "mixed_effects",
}


def _plan_metric_name(plan) -> str:
	"""The persisted metric name a plan reads: the bare outcome metric,
	or its scoped form when the plan registers a sequence scope and the
	metric is one that depends on the sequence view."""
	scope = plan.get("sequence_scope") or "all_actions"
	base = plan.outcome_metric
	if scope != "all_actions" and (base in metrics_api.SCOPED_SEQUENCE_METRICS or base.startswith("path_coherence_v1")):
		return taxonomy.scope_metric_name(base, scope)
	return base


def _primary_test_name(plan, paired: bool) -> str:
	if plan.model_family in _PRIMARY_TEST:
		return _PRIMARY_TEST[plan.model_family]
	return "paired_t" if paired else "welch_t"


def _can_persist() -> bool:
	"""Submission-day plan section 14: a read-only reviewer can compute
	and see a comparison but never adds to the scientific record."""
	return bool(frappe.has_permission("EORL Analysis Result", "create"))


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
		{"run": run_name, "metric_name": metric_name, "episode": ["in", ["", None]],
			"creation": [">=", frappe.db.get_value("EORL Run", run_name, "creation")]},
		["metric_value", "value_undefined"], as_dict=True, order_by="creation desc",
	)
	if existing is not None:
		if existing.value_undefined:
			frappe.throw(f"Metric {metric_name!r} is undefined for run {run_name!r}, so it cannot enter a comparison.")
		return existing.metric_value

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
	n_independent_runs_b, n_episodes_a, n_episodes_b, paired, standardized_effect, mean_a, mean_b,
	effect_ci=None, is_primary=False):
	ci = result.get("ci_95", (None, None))
	effect_ci = effect_ci or {}
	numeric = {
		"mean_a": mean_a, "mean_b": mean_b, "raw_effect": result.get(
			"mean_diff", result.get("observed_diff", result.get("observed_mean_diff", result.get("coefficient")))),
		"standardized_effect": standardized_effect, "ci_95_lower": ci[0] if ci else None, "ci_95_upper": ci[1] if ci else None,
		"p_value": result.get("p_value"), "adjusted_p_value": result.get("adjusted_p_value"),
		"effect_size_ci_low": effect_ci.get("ci_low"), "effect_size_ci_high": effect_ci.get("ci_high"),
	}
	undefined_fields = [k for k, v in numeric.items() if _clean_float(v) is None]
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
			"metric_definition_version": metrics_api.metric_version(_plan_metric_name(plan)),
			"stats_package_version": f"scipy {scipy.__version__}",
			"mean_a": _clean_float(mean_a),
			"mean_b": _clean_float(mean_b),
			"raw_effect": _clean_float(raw_effect),
			"standardized_effect": _clean_float(standardized_effect),
			"ci_95_lower": _clean_float(ci[0]) if ci else None,
			"ci_95_upper": _clean_float(ci[1]) if ci else None,
			"p_value": _clean_float(result["p_value"]),
			"effect_size_ci_low": _clean_float(effect_ci.get("ci_low")),
			"effect_size_ci_high": _clean_float(effect_ci.get("ci_high")),
			"effect_size_ci_method": effect_ci.get("method"),
			"sequence_scope": plan.get("sequence_scope") or "all_actions",
			"family_id": plan.get("multiple_testing_family") or None,
			"is_primary_test": 1 if is_primary else 0,
			"interpretation_label": result.get("interpretation", {}).get("label"),
			"adjusted_p_value": _clean_float(result.get("adjusted_p_value")),
			"undefined_fields": ", ".join(undefined_fields) or None,
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
	frappe.only_for(READ_ROLES)
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

	metric_name = _plan_metric_name(plan)
	values_a = [_run_level_metric(r, metric_name) for r in run_ids_group_a]
	values_b = [_run_level_metric(r, metric_name) for r in run_ids_group_b]
	n_episodes_a = sum(_episode_count(r) for r in run_ids_group_a)
	n_episodes_b = sum(_episode_count(r) for r in run_ids_group_b)

	paired = bool(plan.paired_by)
	permutation_iterations = plan.permutation_iterations or 10000
	seed = plan.get("random_seed") or stats.DEFAULT_BOOTSTRAP_SEED

	if paired:
		_verify_sibling_branches(run_ids_group_a, run_ids_group_b)
		raw_results = [
			stats.paired_t_test(values_a, values_b),
			stats.paired_permutation_test(values_a, values_b, n_iterations=permutation_iterations, seed=seed),
		]
		standardized_effect = stats.paired_hedges_g(values_a, values_b)
	else:
		raw_results = [
			stats.welch_t_test(values_a, values_b),
			stats.permutation_test(values_a, values_b, n_iterations=permutation_iterations, seed=seed),
		]
		standardized_effect = stats.hedges_g(values_a, values_b)

	effect_ci = stats.hedges_g_bootstrap_ci(
		values_a, values_b, paired=paired, n_resamples=plan.bootstrap_iterations or 5000, seed=seed,
	)

	equivalence_bounds = _parse_equivalence_bounds(plan.equivalence_bounds)
	tost = None
	if equivalence_bounds:
		tost = stats.tost_equivalence(values_a, values_b, *equivalence_bounds, alpha=plan.alpha or 0.05)
		raw_results.append(tost)

	primary_name = _primary_test_name(plan, paired)
	primary = next((r for r in raw_results if r["test"] == primary_name), raw_results[0])

	mean_a, mean_b = sum(values_a) / len(values_a), sum(values_b) / len(values_b)
	family = _family_adjustment(plan, primary)
	if family:
		primary["adjusted_p_value"] = family["adjusted_p_for_this_plan"]
	primary["interpretation"] = _interpret(plan, primary, mean_a - mean_b, tost)

	persisted = _can_persist()
	analysis_result_names = []
	if persisted:
		analysis_result_names = [
			_save_analysis_result(
				plan, result, run_ids_group_a, run_ids_group_b,
				len(run_ids_group_a), len(run_ids_group_b), n_episodes_a, n_episodes_b,
				paired, standardized_effect, mean_a, mean_b, effect_ci=effect_ci, is_primary=result is primary,
			)
			for result in raw_results
		]
		if family:
			family = apply_family_adjustment(plan.multiple_testing_family)

	return {
		"analysis_plan": plan.name,
		"persisted": persisted,
		"paired": paired,
		"outcome_metric": plan.outcome_metric,
		"metric_name": metric_name,
		"sequence_scope": plan.get("sequence_scope") or "all_actions",
		"standardized_effect_ci": effect_ci,
		"primary_test": primary_name,
		"interpretation": primary["interpretation"],
		"multiplicity": family,
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
	result["interpretation"] = _interpret(plan, result, mean_a - mean_b)
	persisted = _can_persist()
	analysis_result_name = _save_analysis_result(
		plan, result, run_ids_group_a, run_ids_group_b,
		len(set(run_ids_group_a)), len(set(run_ids_group_b)),
		len(episode_values_a), len(episode_values_b),
		False, None, mean_a, mean_b, is_primary=True,
	) if persisted else None

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
		"persisted": persisted,
		"interpretation": result["interpretation"],
		"results": [result],
		"analysis_result_names": [analysis_result_name] if analysis_result_name else [],
	}


def _interpret(plan, primary: dict, mean_diff: float, tost: dict = None) -> dict:
	p_value = primary.get("adjusted_p_value", primary.get("p_value"))
	try:
		return interpretation.classify(
			expected_direction=plan.get("expected_direction") or "nonzero",
			p_value=_clean_float(p_value), mean_diff=mean_diff, alpha=plan.alpha or 0.05,
			equivalent=tost["equivalent"] if tost else None,
			rules={k: plan.get(k) for k in interpretation.DEFAULT_RULES},
		)
	except ValueError as exc:
		return {"label": "not_evaluated", "cell": f"invalid rule: {exc}"}


def _latest_primary_results(family_id: str) -> list:
	"""The most recent primary-test result of each plan in a family."""
	plans = frappe.get_all("EORL Analysis Plan", filters={"multiple_testing_family": family_id}, pluck="name")
	latest = []
	for plan_name in plans:
		rows = frappe.get_all(
			"EORL Analysis Result", filters={"analysis_plan": plan_name, "is_primary_test": 1},
			fields=["name", "analysis_plan", "p_value", "diagnostics_json"], order_by="creation desc", limit_page_length=1,
		)
		if rows:
			# Prefer the raw p-value in the stored diagnostics: the p_value
			# column cannot hold "undefined" (see _save_analysis_result).
			diagnostics = frappe.parse_json(rows[0].diagnostics_json or "{}") or {}
			if "p_value" in diagnostics:
				rows[0].p_value = _clean_float(diagnostics["p_value"])
			latest.append(rows[0])
	return latest


def _family_adjustment(plan, primary: dict):
	"""In-memory adjustment of this plan's primary p-value against the
	stored primary results of the other plans in its family. Lets a
	reviewer see the adjusted value without anything being written."""
	family_id = plan.get("multiple_testing_family")
	if not family_id:
		return None
	method = plan.get("adjustment_method") or "holm"
	others = [r for r in _latest_primary_results(family_id) if r.analysis_plan != plan.name]
	p_values = [r.p_value for r in others] + [_clean_float(primary.get("p_value"))]
	adjusted = stats.adjust_p_values(p_values, method=method, alpha=plan.alpha or 0.05)
	return {
		"family_id": family_id, "method": method, "family_size": adjusted["family_size"],
		"adjusted_p_for_this_plan": adjusted["adjusted_p"][-1],
		"members": [r.analysis_plan for r in others] + [plan.name],
	}


@frappe.whitelist()
def apply_family_adjustment(family_id: str) -> dict:
	"""Recomputes the adjusted p-value of every plan's latest primary
	result in a multiple-testing family and writes it to those results.
	The adjustment method is read from the family's plans and must agree
	across them."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	methods = set(frappe.get_all("EORL Analysis Plan", filters={"multiple_testing_family": family_id}, pluck="adjustment_method"))
	methods.discard(None)
	if len(methods) > 1:
		frappe.throw(f"Plans in family {family_id!r} declare different adjustment methods: {sorted(methods)}.")
	method = methods.pop() if methods else "holm"
	rows = _latest_primary_results(family_id)
	adjusted = stats.adjust_p_values([r.p_value for r in rows], method=method)
	for row, q in zip(rows, adjusted["adjusted_p"]):
		values = {"family_id": family_id, "adjustment_method": method}
		if q is not None:
			values["adjusted_p_value"] = q
		frappe.db.set_value("EORL Analysis Result", row.name, values, update_modified=False)
	return {
		"family_id": family_id, "method": method, "family_size": adjusted["family_size"],
		"results": [{"analysis_plan": r.analysis_plan, "analysis_result": r.name, "raw_p": r.p_value, "adjusted_p": q}
			for r, q in zip(rows, adjusted["adjusted_p"])],
	}


@frappe.whitelist()
def evaluate_experiment_interpretation(experiment_name: str) -> dict:
	"""Applies each plan's registered interpretation rule to its latest
	stored primary result (with the family-adjusted p-value where there
	is one), then combines the labels with the experiment's registered
	combination rule. A plan with no stored result is not_evaluated."""
	frappe.only_for(READ_ROLES)
	exp = frappe.get_doc("EORL Experiment", experiment_name)
	plans = frappe.get_all("EORL Analysis Plan", filters={"experiment": experiment_name}, pluck="name", order_by="creation asc")
	per_plan, labels, weights = [], [], []
	for plan_name in plans:
		plan = frappe.get_doc("EORL Analysis Plan", plan_name)
		primary = frappe.get_all("EORL Analysis Result", filters={"analysis_plan": plan_name, "is_primary_test": 1},
			fields=["name", "adjusted_p_value", "family_id", "mean_a", "mean_b", "diagnostics_json", "run_ids_group_a", "run_ids_group_b"],
			order_by="creation desc", limit_page_length=1)
		if not primary:
			verdict = {"label": "not_evaluated", "cell": "no_result"}
		else:
			row = primary[0]
			# The TOST computed on exactly the same runs as the primary test.
			tost_rows = frappe.get_all("EORL Analysis Result",
				filters={"analysis_plan": plan_name, "test_family": "tost_equivalence",
					"run_ids_group_a": row.run_ids_group_a, "run_ids_group_b": row.run_ids_group_b},
				fields=["diagnostics_json"], order_by="creation desc", limit_page_length=1)
			tost = frappe.parse_json(tost_rows[0].diagnostics_json) if tost_rows else None
			raw_p = frappe.parse_json(row.diagnostics_json or "{}").get("p_value")
			p = row.adjusted_p_value if row.family_id else raw_p
			verdict = _interpret(plan, {"p_value": p}, (row.mean_a or 0) - (row.mean_b or 0), tost)
			verdict["analysis_result"] = row.name
		per_plan.append({"analysis_plan": plan_name, "outcome_metric": plan.outcome_metric, **verdict})
		labels.append(verdict["label"])
		weights.append(plan.get("interpretation_weight") or 1.0)
	combined = interpretation.combine(labels, exp.get("interpretation_combination") or "AND", weights)
	return {"experiment": experiment_name, "plans": per_plan, "combined": combined}


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
			"effect_size_ci_low", "effect_size_ci_high", "effect_size_ci_method", "adjusted_p_value",
			"family_id", "sequence_scope", "metric_definition_version", "interpretation_label", "run_ids_group_a", "run_ids_group_b",
		],
		order_by="creation asc",
	)
	columns = [
		"test_family", "n_independent_runs_a", "n_independent_runs_b", "n_episodes_a", "n_episodes_b",
		"paired", "mean_a", "mean_b", "raw_effect", "standardized_effect",
		"effect_size_ci_low", "effect_size_ci_high", "effect_size_ci_method",
		"ci_95_lower", "ci_95_upper", "p_value", "adjusted_p_value", "family_id", "sequence_scope",
		"interpretation_label", "metric_definition_version", "stats_package_version", "run_ids_group_a", "run_ids_group_b",
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


@frappe.whitelist()
def compute_power_analysis(standardized_effect: float, n_per_group: int, alpha: float = 0.05, n_simulations: int = 2000,
	seed: int = stats.DEFAULT_BOOTSTRAP_SEED, design: str = "independent") -> dict:
	"""SOTA Milestone 8 (V2 section 49): Monte Carlo power estimate for
	a Welch's t-test at a given standardized effect size and n -- "will
	the test this app actually runs detect an effect of this size,
	with this many runs per group." Simulation-based, not a closed-form
	formula, so it reflects what compare_groups itself will do."""
	frappe.only_for(READ_ROLES)
	seed = int(seed) if seed not in (None, "") else stats.DEFAULT_BOOTSTRAP_SEED
	if design == "paired":
		result = stats.simulate_paired_power(float(standardized_effect), int(n_per_group), alpha=float(alpha), n_simulations=int(n_simulations), seed=seed)
	else:
		result = stats.simulate_power(float(standardized_effect), int(n_per_group), alpha=float(alpha), n_simulations=int(n_simulations), seed=seed)
	result["seed"], result["design"] = seed, design
	result["mc_standard_error"] = (result["power"] * (1 - result["power"]) / result["n_simulations"]) ** 0.5
	return result


@frappe.whitelist()
def compute_power_grid(effects="[0.3, 0.5, 0.8]", ns="[5, 10, 20, 27, 40]", design: str = "independent",
	alpha: float = 0.05, n_simulations: int = 2000, seed: int = stats.DEFAULT_BOOTSTRAP_SEED) -> dict:
	"""Submission-day plan section 12: a seeded table of power by effect
	size and runs per condition, with Monte Carlo standard errors, for
	the independent-groups or the paired-branch design. The same inputs
	always return the same table."""
	frappe.only_for(READ_ROLES)
	effects = frappe.parse_json(effects) if isinstance(effects, str) else effects
	ns = frappe.parse_json(ns) if isinstance(ns, str) else ns
	rows = stats.power_grid([float(e) for e in effects], [int(n) for n in ns], design=design, alpha=float(alpha),
		n_simulations=int(n_simulations), seed=int(seed))
	return {"design": design, "alpha": float(alpha), "seed": int(seed), "n_simulations": int(n_simulations), "rows": rows}


@frappe.whitelist()
def compute_required_sample_size(standardized_effect: float, target_power: float = 0.8, alpha: float = 0.05, max_n: int = 300,
	seed: int = stats.DEFAULT_BOOTSTRAP_SEED) -> dict:
	"""SOTA Milestone 8 (V2 section 49): "how many independent runs per
	group do I need" for a declared standardized effect size and target
	power -- searches upward via compute_power_analysis's same
	simulation rather than a closed-form formula."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	return stats.required_sample_size(
		float(standardized_effect), target_power=float(target_power), alpha=float(alpha), max_n=int(max_n),
		seed=int(seed) if seed not in (None, "") else stats.DEFAULT_BOOTSTRAP_SEED,
	)


@frappe.whitelist()
def compute_replication_diagnostics(analysis_plan_name: str, run_ids_group_a, run_ids_group_b) -> dict:
	"""SOTA Milestone 8 (V2 section 48): 'running mean/effect estimate
	as replications accumulate.' Reads the SAME run-level outcome
	values compare_groups would (one value per run, via the plan's
	outcome_metric), then shows how the Welch mean-difference estimate
	moves as runs 1..n accumulate -- diagnostic, not a new confirmatory
	result, so (deliberately) nothing is persisted as an
	EORL Analysis Result here."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	if isinstance(run_ids_group_a, str):
		run_ids_group_a = frappe.parse_json(run_ids_group_a)
	if isinstance(run_ids_group_b, str):
		run_ids_group_b = frappe.parse_json(run_ids_group_b)

	plan = frappe.get_doc("EORL Analysis Plan", analysis_plan_name)
	values_a = [_run_level_metric(r, _plan_metric_name(plan)) for r in run_ids_group_a]
	values_b = [_run_level_metric(r, _plan_metric_name(plan)) for r in run_ids_group_b]

	trajectory = stats.replication_stability(values_a, values_b)
	for point in trajectory:
		point["ci_95"] = (_clean_float(point["ci_95"][0]), _clean_float(point["ci_95"][1]))
		point["p_value"] = _clean_float(point["p_value"])
	return {"analysis_plan": plan.name, "outcome_metric": plan.outcome_metric, "trajectory": trajectory}


@frappe.whitelist()
def compute_robustness_jackknife(analysis_plan_name: str, run_ids_group_a, run_ids_group_b) -> dict:
	"""SOTA Milestone 8 (V2 section 47, robustness workbench -- scoped
	to a leave-one-run-out sensitivity analysis, forest-plot-ready).
	Same outcome values compare_groups would read; diagnostic only, not
	persisted as an EORL Analysis Result."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	if isinstance(run_ids_group_a, str):
		run_ids_group_a = frappe.parse_json(run_ids_group_a)
	if isinstance(run_ids_group_b, str):
		run_ids_group_b = frappe.parse_json(run_ids_group_b)

	plan = frappe.get_doc("EORL Analysis Plan", analysis_plan_name)
	values_a = [_run_level_metric(r, _plan_metric_name(plan)) for r in run_ids_group_a]
	values_b = [_run_level_metric(r, _plan_metric_name(plan)) for r in run_ids_group_b]

	result = stats.jackknife_sensitivity(values_a, values_b)
	for row in result["rows"]:
		row["ci_95"] = (_clean_float(row["ci_95"][0]), _clean_float(row["ci_95"][1]))
		row["p_value"] = _clean_float(row["p_value"])
		# Replace the generic "Excl. A[i]" label with the actual run name excluded.
		excluded = row["excluded"]
		if excluded:
			run_name = run_ids_group_a[excluded["index"]] if excluded["group"] == "a" else run_ids_group_b[excluded["index"]]
			row["label"] = f"Excl. {run_name}"

	return {
		"analysis_plan": plan.name, "outcome_metric": plan.outcome_metric,
		"rows": result["rows"], "max_single_exclusion_deviation": _clean_float(result["max_single_exclusion_deviation"]),
	}


@frappe.whitelist()
def compute_qap_comparison(run_a: str, run_b: str, n_permutations: int = 5000) -> dict:
	"""SOTA Milestone 9 (V2 section 44.4: "QAP/MRQAP for relational
	hypotheses... do not treat edges as independent observations"):
	are two runs' agent-communication networks more similar than
	chance? Diagnostic, not persisted as an EORL Analysis Result --
	same scoping choice as compute_replication_diagnostics /
	compute_robustness_jackknife above."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	from eorl_lab.api.process import _run_level_metric_json

	network_a = _run_level_metric_json(run_a, "communication_network")
	network_b = _run_level_metric_json(run_b, "communication_network")
	actors = sorted(
		set(network_a) | {t for targets in network_a.values() for t in targets}
		| set(network_b) | {t for targets in network_b.values() for t in targets}
	)

	result = stats.qap_correlation(network_a, network_b, actors, n_permutations=int(n_permutations))
	result["run_a"], result["run_b"], result["actors"] = run_a, run_b, actors
	return result
