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
from typing import List, Optional

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
