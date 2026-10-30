# Reproducibility & Export

## Exporting a run

```python
from eorl_lab.api.exports import export_run_bundle

bundle = export_run_bundle("RUN-00123")
# bundle["episodes"], bundle["events"], bundle["run_manifest"], ...
```

The front end's [Reproducibility / Export page](front-end.md) wraps
this with a downloadable `.zip` bundle containing:

- `run_manifest.json` — an immutable record of exactly what was run
- `architecture.json`, `resolved_agent_configs/` — the full resolved
  configuration, not just links
- `scenario_stream.jsonl`, `events.jsonl` — the raw exogenous stream
  and the complete append-only event trace
- `process_paths.csv`, `metrics.csv` — derived process-mining output
- `model_metadata.json`, `environment_metadata.json`, `code_commit.txt`,
  `requirements_lock.txt` — full provenance
- `README_REPRODUCE.md` — human-readable instructions

## Reproducing a run

```python
from eorl_lab.observability.replay import reproduce_run

result = reproduce_run("RUN-00123")
```

This launches a brand-new run from `RUN-00123`'s own recorded seed,
architecture, and regime shift, then verifies the new run's
scenario-case hashes and computed metrics match the original. Only
works for runs launched via `run_architecture` / `launch_pilot` — older
entrypoints (`run_demo_episode`, `run_specialist_routine`) don't carry
enough configuration to replay, and this fails with a clear error
rather than guessing at defaults.

## Why this works: determinism given (seed, episode, regime_shift)

`eorl_lab.scenarios.procurement.generate_case(seed, episode,
regime_shift)` is a pure function — same inputs always produce the
same case, including its `case_hash`. This is what makes:

- **paired seeds** (two architectures seeing the identical exogenous
  stream — V2 §18) exact, not approximate
- **counterfactual branching**'s shared-history guarantee verifiable
  (two branches' pre-branch-point episodes are provably identical, not
  just similar)
- **reproduction** verifiable rather than just "re-run and hope"
