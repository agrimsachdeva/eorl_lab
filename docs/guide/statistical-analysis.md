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

## Honest limits of this phase

- No mixed-effects/GEE/clustered model exists — `analysis_unit` has
  exactly one supported value (`"run"`) today.
- No multiple-testing correction (V2 §46) and no TOST equivalence
  testing (V2 §45.1) yet.
- Mann-Whitney U and Wilcoxon signed-rank (named in V2 §44.4 as
  "robustness" additions) aren't implemented.
- The Process Explorer (DFG + swimlane), adaptation-trajectory plot,
  and a dedicated distribution-comparison page aren't built as
  graphical UI yet — the underlying data all three would need already
  exists and is reachable (see [Using the Front End](front-end.md) and
  the [API Reference](../reference/analysis.md)).
