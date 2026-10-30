"""SOTA Milestone 5 (V2 section 44): a design-aware statistical
inference engine, deliberately minimal rather than silently wrong.
Thin wrappers around scipy.stats -- scipy's implementations are
correct, fast, and already handle the numerical edge cases properly,
so there is no good reason to hand-roll a t-distribution or a
permutation test from scratch.

Every function here operates on plain lists of floats -- one value per
INDEPENDENT unit (normally one run, never one episode; see
eorl_lab.api.analysis for where that guardrail is actually enforced).
"""
import warnings
from typing import List, Optional

import numpy as np
from scipy import stats as scipy_stats


def _mean(values: List[float]) -> float:
	return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Two independent conditions (V2 section 44.4)
# ---------------------------------------------------------------------------

def welch_t_test(a: List[float], b: List[float]) -> dict:
	"""Welch's t-test (unequal variances) for two independent-unit
	samples, plus a 95% CI on the raw mean difference."""
	if len(a) < 2 or len(b) < 2:
		raise ValueError("welch_t_test needs at least 2 independent units per group")

	result = scipy_stats.ttest_ind(a, b, equal_var=False)
	ci = result.confidence_interval(confidence_level=0.95)

	return {
		"test": "welch_t",
		"mean_a": _mean(a), "mean_b": _mean(b), "mean_diff": _mean(a) - _mean(b),
		"n_a": len(a), "n_b": len(b),
		"t_statistic": float(result.statistic), "df": float(result.df), "p_value": float(result.pvalue),
		"ci_95": (float(ci.low), float(ci.high)),
	}


def permutation_test(
	a: List[float], b: List[float], n_iterations: int = 10000, seed: Optional[int] = None
) -> dict:
	"""Permutation test on the mean difference between two independent
	groups -- no distributional assumption, just reshuffles the pooled
	sample into the original group sizes."""
	if len(a) < 2 or len(b) < 2:
		raise ValueError("permutation_test needs at least 2 independent units per group")

	result = scipy_stats.permutation_test(
		(a, b), statistic=lambda x, y: _mean(x) - _mean(y),
		n_resamples=n_iterations, random_state=seed, alternative="two-sided",
	)
	return {
		"test": "permutation",
		"observed_diff": float(result.statistic),
		"n_iterations": n_iterations,
		"p_value": float(result.pvalue),
	}


def hedges_g(a: List[float], b: List[float]) -> float:
	"""Standardized effect size (Hedges' g: Cohen's d with the
	small-sample bias correction)."""
	n_a, n_b = len(a), len(b)
	var_a, var_b = scipy_stats.tvar(a), scipy_stats.tvar(b)
	pooled_sd = ((((n_a - 1) * var_a) + ((n_b - 1) * var_b)) / (n_a + n_b - 2)) ** 0.5
	if pooled_sd == 0.0:
		return 0.0
	d = (_mean(a) - _mean(b)) / pooled_sd
	correction = 1.0 - (3.0 / (4.0 * (n_a + n_b - 2) - 1.0))
	return float(d * correction)


# ---------------------------------------------------------------------------
# Paired / matched comparisons (V2 section 44.3 -- counterfactual branches
# sharing identical history up to the branch point)
# ---------------------------------------------------------------------------

def paired_t_test(a: List[float], b: List[float]) -> dict:
	"""Paired t-test -- the correct test once two conditions are
	matched (e.g. sibling counterfactual branches), instead of
	(wrongly) treating them as two independent groups."""
	if len(a) != len(b):
		raise ValueError("paired_t_test requires equal-length, position-matched samples")
	if len(a) < 2:
		raise ValueError("paired_t_test needs at least 2 pairs")

	result = scipy_stats.ttest_rel(a, b)
	ci = result.confidence_interval(confidence_level=0.95)
	diffs = [x - y for x, y in zip(a, b)]

	return {
		"test": "paired_t", "n_pairs": len(a), "mean_diff": _mean(diffs),
		"t_statistic": float(result.statistic), "df": float(result.df), "p_value": float(result.pvalue),
		"ci_95": (float(ci.low), float(ci.high)),
	}


def paired_permutation_test(
	a: List[float], b: List[float], n_iterations: int = 10000, seed: Optional[int] = None
) -> dict:
	"""Paired permutation test: randomly flips the sign of each pair's
	difference (the only label-preserving randomization valid under
	pairing) rather than reshuffling the pooled sample."""
	if len(a) != len(b):
		raise ValueError("paired_permutation_test requires equal-length, position-matched samples")
	if len(a) < 2:
		raise ValueError("paired_permutation_test needs at least 2 pairs")

	diffs = [x - y for x, y in zip(a, b)]
	result = scipy_stats.permutation_test(
		(diffs,), statistic=lambda d, axis: scipy_stats.describe(d, axis=axis).mean,
		permutation_type="samples", n_resamples=n_iterations, random_state=seed, alternative="two-sided",
	)
	return {
		"test": "paired_permutation", "observed_mean_diff": _mean(diffs),
		"n_iterations": n_iterations, "p_value": float(result.pvalue),
	}


def paired_hedges_g(a: List[float], b: List[float]) -> float:
	"""Standardized effect size for paired data: mean difference over
	the SD of the differences (not the pooled between-group SD --
	that would ignore the pairing's variance reduction)."""
	diffs = [x - y for x, y in zip(a, b)]
	sd = scipy_stats.tstd(diffs)
	if sd == 0.0:
		return 0.0
	n = len(diffs)
	correction = 1.0 - (3.0 / (4.0 * (n - 1) - 1.0))
	return float((_mean(diffs) / sd) * correction)


# ---------------------------------------------------------------------------
# Equivalence testing (V2 section 45.1): SOTA Milestone 6
# ---------------------------------------------------------------------------

def _welch_se_df(a: List[float], b: List[float]):
	n_a, n_b = len(a), len(b)
	se_a2, se_b2 = scipy_stats.tvar(a) / n_a, scipy_stats.tvar(b) / n_b
	se = (se_a2 + se_b2) ** 0.5
	if se == 0.0:
		return 0.0, n_a + n_b - 2
	df = (se_a2 + se_b2) ** 2 / ((se_a2 ** 2) / (n_a - 1) + (se_b2 ** 2) / (n_b - 1))
	return se, df


def tost_equivalence(a: List[float], b: List[float], low_bound: float, high_bound: float, alpha: float = 0.05) -> dict:
	"""Two One-Sided Tests (TOST) for equivalence (V2 section 45.1): the
	researcher declares equivalence bounds BEFORE running this -- the
	caller is responsible for that (EORL Analysis Plan.equivalence_bounds
	is saved before inferential results are generated, same discipline
	as the rest of the Analysis Plan). Equivalence is established only
	if the mean difference is significantly within BOTH bounds -- the
	TOST p-value is the MAX of the two one-sided p-values, not their
	average or minimum."""
	if len(a) < 2 or len(b) < 2:
		raise ValueError("tost_equivalence needs at least 2 independent units per group")
	if low_bound >= high_bound:
		raise ValueError(f"low_bound ({low_bound}) must be < high_bound ({high_bound})")

	mean_diff = _mean(a) - _mean(b)
	se, df = _welch_se_df(a, b)

	if se == 0.0:
		equivalent = low_bound < mean_diff < high_bound
		return {
			"test": "tost_equivalence", "mean_diff": mean_diff,
			"low_bound": low_bound, "high_bound": high_bound, "alpha": alpha,
			"p_value_lower": 0.0 if equivalent else 1.0, "p_value_upper": 0.0 if equivalent else 1.0,
			"p_value": 0.0 if equivalent else 1.0, "equivalent": equivalent,
		}

	t_lower = (mean_diff - low_bound) / se
	t_upper = (mean_diff - high_bound) / se
	p_lower = float(scipy_stats.t.sf(t_lower, df))   # H0: true diff <= low_bound
	p_upper = float(scipy_stats.t.cdf(t_upper, df))  # H0: true diff >= high_bound
	p_value = max(p_lower, p_upper)

	return {
		"test": "tost_equivalence", "mean_diff": mean_diff,
		"low_bound": low_bound, "high_bound": high_bound, "alpha": alpha,
		"p_value_lower": p_lower, "p_value_upper": p_upper,
		"p_value": p_value, "equivalent": p_value < alpha,
	}


# ---------------------------------------------------------------------------
# Mixed-effects model (V2 section 44.2's "explicit hierarchical
# specification" alternative to the independence guardrail's block):
# SOTA Milestone 6
# ---------------------------------------------------------------------------

def mixed_effects_comparison(
	episode_values_a: List[float], run_ids_a: List[str],
	episode_values_b: List[float], run_ids_b: List[str],
) -> dict:
	"""A genuine two-level model for EPISODE-level outcomes, with RUN
	as the random-effect cluster -- this is what makes analysis at the
	episode level honest (V2 section 44.2): episodes are modeled as
	correlated observations nested within their own run, not as
	independent rows. Every element of `episode_values_a` must have a
	corresponding run id in `run_ids_a` at the same position (same for
	b) -- multiple episodes from the same run share the same run id."""
	import pandas as pd
	import statsmodels.formula.api as smf

	if len(episode_values_a) != len(run_ids_a) or len(episode_values_b) != len(run_ids_b):
		raise ValueError("episode_values and run_ids must be the same length within each group")
	if len(set(run_ids_a)) < 2 or len(set(run_ids_b)) < 2:
		raise ValueError("mixed_effects_comparison needs at least 2 distinct run clusters per group")

	rows = [{"value": v, "condition": "A", "run_cluster": r} for v, r in zip(episode_values_a, run_ids_a)]
	rows += [{"value": v, "condition": "B", "run_cluster": r} for v, r in zip(episode_values_b, run_ids_b)]
	frame = pd.DataFrame(rows)

	model = smf.mixedlm("value ~ condition", frame, groups=frame["run_cluster"])
	# A degenerate input (e.g. zero variance within every cluster -- a
	# real case this hits when every episode in both groups has the
	# identical outcome) can leave the optimizer unable to converge.
	# fit.converged already carries that signal for callers to check;
	# the warning itself is just log noise once that signal exists.
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		fit = model.fit()

	# The condition coefficient is whichever non-intercept term patsy
	# created for the categorical "condition" column -- read it by
	# position rather than hard-coding the exact "condition[T.B]"-style
	# label, which is a formatting detail that can vary.
	condition_term = [name for name in fit.params.index if name != "Intercept"][0]
	ci = fit.conf_int().loc[condition_term]

	return {
		"test": "mixed_effects",
		"coefficient": float(fit.params[condition_term]),
		"p_value": float(fit.pvalues[condition_term]),
		"ci_95": (float(ci[0]), float(ci[1])),
		"n_episodes_a": len(episode_values_a), "n_episodes_b": len(episode_values_b),
		"n_clusters_a": len(set(run_ids_a)), "n_clusters_b": len(set(run_ids_b)),
		"converged": bool(fit.converged),
		"group_variance": float(fit.cov_re.iloc[0, 0]),
	}


# ---------------------------------------------------------------------------
# Power / precision planning (V2 section 49): SOTA Milestone 8
# ---------------------------------------------------------------------------

def simulate_power(standardized_effect: float, n_per_group: int, alpha: float = 0.05, n_simulations: int = 2000, seed: Optional[int] = None) -> dict:
	"""Monte Carlo power estimate for a Welch's t-test (V2 section 49):
	repeatedly draws two normal samples of size `n_per_group`, one
	shifted by `standardized_effect` standard deviations from the
	other, runs welch_t_test, and reports the fraction of simulated
	draws that reached significance at `alpha`. Deliberately simulation
	-based rather than a closed-form formula -- it reuses the exact
	same test function `compare_groups` actually runs, so the power
	estimate is honest about what this app's own test will detect,
	not a generic textbook formula that may not match."""
	if n_per_group < 2:
		raise ValueError("simulate_power needs n_per_group >= 2")
	generator = np.random.default_rng(seed)

	significant = 0
	for _ in range(n_simulations):
		a = generator.normal(loc=standardized_effect, scale=1.0, size=n_per_group)
		b = generator.normal(loc=0.0, scale=1.0, size=n_per_group)
		result = welch_t_test(list(a), list(b))
		if result["p_value"] is not None and result["p_value"] < alpha:
			significant += 1

	return {
		"standardized_effect": standardized_effect, "n_per_group": n_per_group, "alpha": alpha,
		"n_simulations": n_simulations, "power": significant / n_simulations,
	}


def required_sample_size(standardized_effect: float, target_power: float = 0.8, alpha: float = 0.05, max_n: int = 300, n_simulations: int = 1000, seed: Optional[int] = None) -> dict:
	"""Searches n_per_group upward (by small steps, then narrowing) via
	simulate_power until the simulated power first reaches
	`target_power`, or reports that `max_n` wasn't enough rather than
	guessing past what was actually checked."""
	step = 1
	n = 2
	last_power = 0.0
	while n <= max_n:
		result = simulate_power(standardized_effect, n, alpha=alpha, n_simulations=n_simulations, seed=seed)
		last_power = result["power"]
		if last_power >= target_power:
			return {
				"standardized_effect": standardized_effect, "target_power": target_power, "alpha": alpha,
				"required_n_per_group": n, "achieved_power": last_power, "searched_up_to": n,
			}
		step = max(1, n // 4)
		n += step

	return {
		"standardized_effect": standardized_effect, "target_power": target_power, "alpha": alpha,
		"required_n_per_group": None, "achieved_power": last_power, "searched_up_to": max_n,
	}


# ---------------------------------------------------------------------------
# Replication and robustness diagnostics (V2 sections 47, 48): SOTA
# Milestone 8
# ---------------------------------------------------------------------------

def replication_stability(a: List[float], b: List[float]) -> list:
	"""V2 section 48: 'running mean/effect estimate as replications
	accumulate.' Recomputes the Welch mean difference and 95% CI using
	only the first n runs of each group, for n = 2..len(group) -- shows
	how much the estimate still moves as more independent replications
	are added, rather than just reporting the final-N estimate as if it
	were stable from the start."""
	n_max = min(len(a), len(b))
	if n_max < 2:
		raise ValueError("replication_stability needs at least 2 runs per group")

	trajectory = []
	for n in range(2, n_max + 1):
		result = welch_t_test(a[:n], b[:n])
		trajectory.append({"n_per_group": n, "mean_diff": result["mean_diff"], "ci_95": result["ci_95"], "p_value": result["p_value"]})
	return trajectory


def jackknife_sensitivity(a: List[float], b: List[float]) -> dict:
	"""V2 section 47 (robustness workbench): a leave-one-run-out
	sensitivity analysis -- the full-sample Welch estimate, plus one
	re-estimate per excluded run (from either group), so a single
	unusual run's influence on the result is visible rather than
	hidden inside an aggregate. Forest-plot-ready: every row is a
	(label, mean_diff, ci_95) triple on the same scale as the baseline."""
	if len(a) < 3 or len(b) < 3:
		raise ValueError("jackknife_sensitivity needs at least 3 runs per group (2 remaining after exclusion)")

	baseline = welch_t_test(a, b)
	rows = [{"label": "Full sample", "excluded": None, "mean_diff": baseline["mean_diff"], "ci_95": baseline["ci_95"], "p_value": baseline["p_value"]}]

	for i in range(len(a)):
		reduced_a = a[:i] + a[i + 1:]
		result = welch_t_test(reduced_a, b)
		rows.append({
			"label": f"Excl. A[{i}]", "excluded": {"group": "a", "index": i},
			"mean_diff": result["mean_diff"], "ci_95": result["ci_95"], "p_value": result["p_value"],
		})
	for i in range(len(b)):
		reduced_b = b[:i] + b[i + 1:]
		result = welch_t_test(a, reduced_b)
		rows.append({
			"label": f"Excl. B[{i}]", "excluded": {"group": "b", "index": i},
			"mean_diff": result["mean_diff"], "ci_95": result["ci_95"], "p_value": result["p_value"],
		})

	diffs = [row["mean_diff"] for row in rows[1:]]
	max_deviation = max(abs(d - baseline["mean_diff"]) for d in diffs) if diffs else 0.0

	return {"baseline": baseline, "rows": rows, "max_single_exclusion_deviation": max_deviation}
