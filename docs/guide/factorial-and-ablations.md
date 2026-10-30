# Factorial Designs & Ablations

## Factorial designs

See [Building an Experiment](building-an-experiment.md) step 4 for the
walkthrough. The short version: `EORL Experiment.factors` (an `EORL
Experiment Factor` child table) generalizes the original fixed
`architecture_a`/`architecture_b` pair into a real N-factor, K-level
design. `EORLExperiment.cell_count()` returns the product of each
distinct `factor_name`'s level count, and `factorial_cells()` returns
the full cartesian product for `launch_pilot` to iterate over.

This is fully backward compatible: leave `factors` empty and every
method (`cell_count`, `total_run_count`, `validate_experiment`,
`launch_pilot`) takes the original 1-factor/2-level code path,
unchanged.

## Ablation marking

> V2 spec, section 19: *"Provide an interface for marking a run as an
> ablation of another configuration."*

This is read literally — a thin marking interface, not a new engine.
To mark a run as an ablation of a baseline:

```python
from eorl_lab.api.runs import mark_ablation

mark_ablation(
    run="RUN-00123",
    baseline_run="RUN-00100",
    mechanism="memory_disabled",   # or "tool_breadth_reduced", "communication_removed", ...
)
```

This sets `EORL Run.is_ablation_of` and `.ablation_mechanism`, and
emits a `run_marked_ablation` event. It doesn't configure or toggle
anything itself — you produce the ablated run the normal way, by
varying the relevant `EORL Tool Policy` / `EORL Memory Profile` /
`EORL Communication Policy` field between the baseline and the ablated
run, then mark the relationship after the fact.

### Ablation vs. branching — don't confuse these

- **`branch_run()`** ([Counterfactual Branching](branching.md)) shares
  *history*: episodes 1..t are identical between parent and branch by
  construction.
- **`mark_ablation()`** shares nothing automatically. An ablation is a
  completely separate full run with one mechanism deliberately
  toggled, compared against a baseline — exactly how the spec's own
  examples work (memory ablation, tool ablation, communication
  ablation, each a separate complete run, not a branch).

A run can, in principle, be both a branch of one run and marked as an
ablation of another; the two fields are independent.
