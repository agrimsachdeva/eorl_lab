# Statistical Analysis

## The independence guardrail, enforced

> V2 spec, section 44.2: *"Episodes inside one run are not independent
> replications."*

If one run has 150 episodes, that is not `n=150` for a between-
architecture comparison — it's `n=1`, with 150 *correlated*
observations from the same organizational history. `eorl_lab.api
.analysis.compare_groups` is the **only** entrypoint in this app that
runs a between-condition statistical comparison, and it enforces this
rather than trusting the caller:

```python
from eorl_lab.api.analysis import compare_groups

result = compare_groups(
    "My Analysis Plan",
    run_ids_group_a=["RUN-00094", "RUN-00095", "RUN-00096", "RUN-00097", "RUN-00098"],
    run_ids_group_b=["RUN-00089", "RUN-00090", "RUN-00091", "RUN-00092", "RUN-00093"],
)
```

This refuses outright (`frappe.ValidationError`) if `EORL Analysis
Plan.analysis_unit != "run"`. There's no honest "explicit hierarchical
specification" fallback yet (that needs a mixed-effects/GEE model —
P1, not built) — so unlike the full spec's two options for this
situation, this phase only has the "block" one.

Every outcome value it reads is **one number per run**: a persisted,
run-level `EORL Metric` row (computed via `compute_run_metrics` if not
already there). It reports — and persists on every `EORL Analysis
Result` — both `N independent runs` and `N episodes`, never conflating
the two.

## Setting up an Analysis Plan

```python
plan = frappe.get_doc({
    "doctype": "EORL Analysis Plan",
    "plan_name": "Broad Autonomy vs Specialist Handoff — Actor Continuity",
    "research_question": "Does broad autonomy increase actor continuity?",
    "outcome_metric": "actor_continuity",   # any eorl_lab.api.metrics.compute_run_metrics metric name
    "analysis_unit": "run",                 # the guardrail field -- always "run" today
    "contrast": "Broad Autonomy vs Specialist Handoff",
    "permutation_iterations": 5000,
}).insert()
```

## What you get back

`compare_groups` always computes **both** the parametric and the
distribution-free test for whichever pairing mode applies — it never
silently picks one for you (V2 §44.4):

- **Independent groups** (the default, `paired_by` unset): Welch's
  t-test + a permutation test on the mean difference, plus Hedges' g
  as the standardized effect.
- **Paired/matched** (`paired_by = "branch_point"`): a paired t-test +
  a paired (sign-flip) permutation test on the per-pair differences,
  plus a paired Hedges' g.

Every test result is saved as its own `EORL Analysis Result` row —
naming the exact run IDs in both groups, the metric version, the scipy
version, and the full raw result as JSON (V2 §52's provenance
requirement).

## Paired comparisons are verified, not just declared

Setting `paired_by` doesn't just change which test runs. `compare_groups`
**verifies** that every `(group_a[i], group_b[i])` pair is a genuine
sibling counterfactual-branch pair — same `parent_run`, same
`branch_point_episode` — before treating them as matched (V2 §44.3).
Claim a pairing that isn't real, and it throws rather than silently
falling back to an unpaired test:

```python
# branch_1 and branch_2 both came from branch_run(parent, branch_episode=5, ...)
plan.paired_by = "branch_point"
plan.save()

compare_groups(plan.name, [branch_1], [branch_2])  # verified, proceeds
compare_groups(plan.name, [some_unrelated_run], [branch_2])  # throws
```

See [Counterfactual Branching](branching.md) for how sibling branches
are created in the first place.

## Using the Scientific Cockpit

`/app/eorl-scientific-cockpit` wraps all of this: pick a saved Analysis
Plan and two groups of runs, click Compare, and see independent-run
count, episode count, means, standardized effect, and both tests'
p-values/CIs as KPI cards — each with a link straight to its full
`EORL Analysis Result` record.

## A worked, live example

Comparing `actor_continuity` across 5 `broad_autonomy` runs vs. 5
`specialist_handoff` runs (3 episodes each) gave:

- Broad autonomy: continuity = **1.0 for every single run** (an actual
  consequence of the architecture — one actor does everything, so
  there's structurally nothing to be discontinuous about)
- Specialist handoff: mean continuity = **0.713**, with real
  variance across runs
- Welch's t: t=99.0, df=4, **p=6.2×10⁻⁸**
- Permutation test (5000 resamples): **p=0.0079**

Two structurally different test families — one parametric, one making
no distributional assumption at all — agreeing the effect is real.

## Equivalence testing (TOST)

> V2 spec, section 45.1: *"The researcher must declare equivalence
> bounds before running the test."*

Set `EORL Analysis Plan.equivalence_bounds` to `"low,high"` and
`compare_groups` automatically runs and persists a `tost_equivalence`
result alongside the usual difference tests:

```python
plan.equivalence_bounds = "-0.1,0.1"
plan.save()

result = compare_groups(plan.name, runs_a, runs_b)
# result["results"] now includes a third entry: {"test": "tost_equivalence", ...}
```

TOST answers a genuinely different question than Welch/permutation —
"are these close enough to call the same," not "are these different."
The two one-sided p-values are combined by taking their **max**:
equivalence is only established if the difference is significantly
within *both* bounds. A live example makes the distinction concrete:
comparing two structurally identical `broad_autonomy` architectures on
`actor_continuity` (which is architecturally exactly 1.0 for every
broad_autonomy run) — Welch's t and the permutation test can't say
anything useful (`nan` and `p=1.0`, correctly inconclusive on
zero-variance data), but TOST confidently establishes equivalence
(`p=0.0`). That's the point of having both: a difference test's
failure to reject isn't evidence of equivalence, but TOST, built for
exactly this question, can actually say so.

## Episode-level analysis with a mixed-effects model

Setting `analysis_unit = "run"` (the default) is the independent-units
path described above. Setting it to `"episode"` is normally refused —
*unless* `model_family = "mixed_effects"` is also set, which is the
"explicit hierarchical specification" V2 section 44.2 offers as the
honest alternative to blocking:

```python
plan.analysis_unit = "episode"
plan.model_family = "mixed_effects"
plan.outcome_metric = "success_rate"   # the only metric with a real per-episode value today
plan.save()

result = compare_groups(plan.name, runs_a, runs_b)
# result["results"][0] == {"test": "mixed_effects", "coefficient": ..., "p_value": ...,
#                           "n_clusters_a": ..., "converged": ..., ...}
```

This fits a genuine two-level model (`statsmodels`' `MixedLM`) with
**run as the random-effect cluster** — episodes are modeled as
correlated observations nested within their own run, never as
independent rows, even though every individual episode contributes to
the fit. `n_independent_runs_a`/`b` on the saved result are cluster
counts; `n_episodes_a`/`b` are the real episode counts used.

**Honest scope**: this only works for `outcome_metric = "success_rate"`
today — mapped directly to each `EORL Episode.success`. Every other
metric this app computes (`sequence_entropy`, `actor_continuity`, ...)
is a genuine run-level aggregate over an entire run's episode paths
with no single-episode definition, so `compare_groups` throws a clear
error naming exactly this if asked for one at the episode level,
rather than fabricating a per-episode value that doesn't mean anything.

## Publication table export

```python
from eorl_lab.api.analysis import export_results_table

export_results_table("My Analysis Plan", fmt="markdown")  # or fmt="csv"
```

Every `EORL Analysis Result` for a plan, in the order they were
computed. This is a plain table export (V2 §50 scoped down) — not the
full journal-formatted "Results Table Generator" with significance
stars and footnotes that section ultimately describes.

## Power and precision planning

```python
from eorl_lab.api.analysis import compute_power_analysis, compute_required_sample_size

compute_power_analysis(standardized_effect=0.8, n_per_group=20)
# {"power": 0.86, "n_simulations": 2000, ...}

compute_required_sample_size(standardized_effect=0.8, target_power=0.8)
# {"required_n_per_group": 27, "achieved_power": 0.81, ...}
```

Both are genuine Monte Carlo simulations of the *exact* Welch's t-test
`compare_groups` runs — not a textbook closed-form formula — so the
estimate reflects what this app's own test will actually detect.
`required_sample_size` searches upward and reports `None` plus how far
it searched, rather than extrapolating, if the ceiling you gave it
isn't enough. The [Power / Precision Planner](front-end.md) page wraps
both as simple forms.

## Replication and robustness diagnostics

```python
from eorl_lab.api.analysis import compute_replication_diagnostics, compute_robustness_jackknife

compute_replication_diagnostics(plan.name, runs_a, runs_b)
# {"trajectory": [{"n_per_group": 2, "mean_diff": ..., "ci_95": ...}, ...]}

compute_robustness_jackknife(plan.name, runs_a, runs_b)
# {"rows": [{"label": "Full sample", ...}, {"label": "Excl. RUN-00042", ...}, ...],
#  "max_single_exclusion_deviation": ...}
```

Both read the same run-level outcome values `compare_groups` would.
**Neither is persisted as an `EORL Analysis Result`** — these are
exploratory robustness checks on an existing comparison, not new
confirmatory results, so recording them as if they were would
misrepresent what they are. Replication diagnostics show whether the
effect estimate is still moving as more runs accumulate (V2 §48);
the jackknife shows whether any single run is quietly driving the
whole result (V2 §47). The
[Robustness & Replication Diagnostics](front-end.md) page renders the
first as a line chart and the second as a forest plot.

## Network comparison (QAP)

```python
from eorl_lab.api.analysis import compute_qap_comparison

compute_qap_comparison("RUN-00130", "RUN-00131")
# {"observed_correlation": 1.0, "p_value": 0.044, "valid_permutations": 2000, "n_actors": 4, ...}
```

Are two runs' agent-communication networks more similar than chance?
Significance comes from permuting one network's **actor labels**
(never its own internal edge structure) and recomputing the
correlation, not an ordinary i.i.d. significance test — edges that
share an actor aren't independent observations of each other, so a
standard correlation p-value would be wrong. **A real mathematical
limit worth knowing**: with this system's typical 1–4 actors, the
permutation space is tiny (4 actors → 4! = 24 relabelings), so the
smallest p-value this test can ever report is 1/24 ≈ 0.042 — not a
bug, just an honest consequence of comparing small networks. The
[Network Explorer](front-end.md) page's second section wraps this.

## Survival analysis (time to recovery)

```python
from eorl_lab.api.process import get_survival_analysis_data

get_survival_analysis_data(["RUN-1", "RUN-2", "RUN-3", "RUN-4"])
# {"survival_function": [{"time": 0.0, "survival_probability": 1.0}, ...],
#  "median_recovery_time": 2.0, "n_events": 3, "n_censored": 1, "runs": [...]}
```

A Kaplan-Meier estimate of episodes-to-recovery after a regime shift,
via each run's own `episodes_to_recover` value. A run that never
recovers within its observed episodes becomes a **right-censored**
observation at its own last post-shock episode — never a dropped data
point, and never silently counted as "recovered." Uses `lifelines`,
not a hand-rolled estimator — a real KM curve has enough edge cases
(ties, censoring at the same time as an event) to be worth the
dependency. The [Survival Analysis](front-end.md) page renders the
curve and a per-run table.

## Honest limits of this phase

- No multiple-testing correction (V2 §46) — not even when a plan's
  `equivalence_bounds` adds a third test family to a comparison that
  already ran two difference tests, or across a robustness workbench's
  many jackknife re-estimates.
- Mann-Whitney U and Wilcoxon signed-rank (named in V2 §44.4 as
  "robustness" additions) aren't implemented.
- `simulate_power`/`required_sample_size` are scoped to the two-
  independent-groups Welch test specifically — power for a paired
  comparison, a mixed-effects model, or TOST equivalence isn't
  estimated.
- Only Kaplan-Meier is implemented; `lifelines` also supports Cox
  proportional-hazards regression (recovery time as a function of
  covariates like architecture), which isn't built.
- A dedicated paired-branch inference UI, cross-filtering between
  panels, and the Theory Compiler wizard aren't built as graphical
  pages yet.
