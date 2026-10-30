# Building an Experiment

This is the real end-to-end researcher workflow: from a theoretical
question to launched runs you can compare.

## 1. Decide your focal construct (optional but recommended)

Browse the [Construct Registry](constructs.md) for a theoretical
construct that matches your research question — e.g. "Routine
coherence" or "Adaptive repertoire", the two with real, working
measurement functions today. You'll link this on the Experiment later
(`focal_construct`).

## 2. Compose your architectures

Build (or reuse) the `EORL Architecture` document(s) you want to
compare — see [Architectures & Agents](architectures-and-agents.md).
At minimum you need one; a factorial design needs as many as you have
levels for your "architecture" factor.

## 3. Create the `EORL Experiment` (or scaffold one from a theory)

If you're starting from a filled-in theory rather than from the
`EORL Experiment` form directly, the **Theory Compiler**
(`/app/eorl-theory-compiler`, backed by
`eorl_lab.api.experiments.compile_theory`) is a structured wizard —
explicitly not autonomous theory generation (V2 §21's own wording) —
that takes your theoretical definition, proposed mechanism,
manipulation, counterfactual condition, outcomes, mediating process
measures, and boundary conditions, and scaffolds the `EORL Experiment`
below plus a matching `EORL Analysis Plan` in one step. If your focal
construct already has a real measurement function (Routine coherence,
Adaptive repertoire), `outcome_metric` on the generated plan is
auto-filled from it; otherwise it's left as an explicit placeholder —
never a guessed metric name. Either way you land back at step 4 below
with a real Experiment to keep configuring.

Otherwise, create the `EORL Experiment` directly:

```python
exp = frappe.get_doc({
    "doctype": "EORL Experiment",
    "experiment_name": "Does broader autonomy change routine coherence?",
    "research_question": "...",
    "theoretical_mechanism": "...",
    "focal_construct": "Routine coherence",
    "architecture_a": "Specialist Handoff",   # fallback / default architecture
    "episode_count": 20,
    "repetitions_per_cell": 10,
    "seed_strategy": "paired",   # every cell in a repetition sees the identical scenario stream
    "base_seed": 42,
}).insert()
```

If you only need the **original 1-factor, up-to-2-level design**
(`architecture_a` vs. optional `architecture_b`), you're done — skip to
step 5. This is still fully supported, unchanged, and is the simpler
path for a two-condition comparison.

## 4. (Optional) Define a real factorial design

Add rows to `exp.factors` (an `EORL Experiment Factor` child table).
Every row sharing the same `factor_name` is one **level** of that
factor; the experiment's cell count is the product of each distinct
factor's level count.

```python
exp.factors = [
    {"factor_name": "architecture", "level_label": "Specialist", "factor_type": "architecture",
     "architecture": "Specialist Handoff", "is_baseline": 1},
    {"factor_name": "architecture", "level_label": "Broad Autonomy", "factor_type": "architecture",
     "architecture": "Broad Autonomy"},
    {"factor_name": "regime", "level_label": "No Shock", "factor_type": "regime_shift", "is_baseline": 1},
    {"factor_name": "regime", "level_label": "Demand Shock", "factor_type": "regime_shift",
     "regime_shift": "Demand Shock Q3"},
]
exp.save()
```

This gives a real 2×2 design — 4 cells. **Today's factor types are
limited to `architecture` and `regime_shift`** — the two independent
knobs `run_architecture()` actually exposes. Wanting to vary model
provider or memory backend as a factor? Build separate `EORL
Architecture` documents (pointing at Agent Templates with different
Model/Memory Profiles) and treat that as your `architecture` factor —
`actor_slots` bind specific agent templates, so model/memory can't be
varied independently of architecture yet.

## 5. Validate, then launch

```python
from eorl_lab.api.experiments import validate_experiment, launch_pilot

validation = validate_experiment(exp.name)
assert validation["valid"], validation["errors"]

result = launch_pilot(exp.name)   # repetitions defaults to repetitions_per_cell
for run_info in result["runs"]:
    print(run_info["cell"] if "cell" in run_info else run_info["architecture"], run_info["success"])
```

`launch_pilot` runs every cell × repetition **synchronously within the
request** (a deliberate Milestone 6 deviation — queued/background
execution for large designs is future work). `seed_strategy: "paired"`
gives every cell in the same repetition the identical seed, so you're
comparing structures against the *identical* exogenous scenario
stream, not different luck.

## 6. Compare and analyze

See [Reproducibility & Export](reproducibility.md) for pulling full
traces, and [Using the Front End](front-end.md)'s Compare Runs page for
a quick side-by-side of coherence/variety metrics across the runs
`launch_pilot` just produced.
