# Counterfactual Branching

> V2 spec, section 17 / 31.5's acceptance test: clone a run's state at
> episode *t*, launch N branches sharing identical history up to that
> point, then let them diverge.

## Branching a run

```python
from eorl_lab.runtime.orchestrator import branch_run, get_full_branch_history

branch_a = branch_run(
    "RUN-00050", branch_episode=5, additional_episode_count=5,
    architecture_name="Broad Autonomy",      # the counterfactual intervention
    intervention_description="continues broad_autonomy unchanged",
)
branch_b = branch_run(
    "RUN-00050", branch_episode=5, additional_episode_count=5,
    architecture_name="Specialist Handoff",  # a genuinely different intervention
    intervention_description="switches to specialist_handoff after episode 5",
)
```

Both branches:

- continue the **same exogenous scenario stream** (identical
  `run_seed`), so episodes 6+ see the same cases the parent would have
  — the intervention is the architecture (or regime shift), not luck
- clone the parent's **actor memory** accumulated through the branch
  episode (`EORL Memory Record` rows are copied, not referenced —
  each branch's actors start with the same accumulated memory the
  parent had, then diverge independently from there)
- **never duplicate episode data** — episodes 1..5 stay owned by the
  parent run

## Reconstructing one continuous history

```python
history_a = get_full_branch_history(branch_a["branch_run"])
history_b = get_full_branch_history(branch_b["branch_run"])

# history_a[:5] == history_b[:5]: same run, same episode names, same
# scenario_case_id, same phase -- byte-identical through the branch point.
# history_a[5:] and history_b[5:]: distinct episodes, owned by their
# respective branch runs.
```

This walks the `parent_run` / `branch_point_episode` chain back to the
root and reads each ancestor's own episodes up to wherever the next
descendant diverged — it never copies data between runs, only changes
which run the read comes from.

## The honest limit: ERP state is not forked

**Every branch's post-branch-point tool calls create real, permanent
ERPNext documents in the same shared company.** There is no per-branch
isolated universe at the ERP layer (that would need per-branch site
clones — V2 §20's "scalable strategy", not built). Concretely:

- Two branches each create their own, distinct `Purchase Order` — never
  a shared/duplicated document
- But both branches' Purchase Orders reference the **same** `company`,
  the same `Item` master data, the same supplier master data

So: **process/event-derived comparisons are valid** across branches
(paths, coherence, variety, actor continuity — these derive purely from
each branch's own events). **Comparisons against absolute shared ERP
aggregates are not** (e.g. "current stock level" — multiple branches
mutate the same underlying ledger concurrently).

## What `branch_run` requires

The source run must have already reached `branch_episode` (it throws
otherwise), and must have an architecture name recoverable from its own
snapshot — i.e. it was launched via `run_architecture` / `launch_pilot`,
not `run_demo_episode` or `run_specialist_routine` — unless you pass
`architecture_name` explicitly.
