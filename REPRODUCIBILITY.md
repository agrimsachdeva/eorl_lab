# Reproducibility

## What is fixed for every run

| Item | Where it is recorded |
|---|---|
| Seed | `EORL Run.run_seed` |
| Architecture, agents, resolved model/memory/tool-policy contents | `architecture_snapshot_json`, `agent_snapshots_json` (frozen at launch) |
| Regime shift | `regime_shift_snapshot_json` |
| Routine template, scenario generator, outcome model | `scenario_snapshot_json`, `routine_template` |
| Actor engine | `actor_engine` |
| Code commit at launch | `code_commit` |
| Experiment and cell | `experiment`, `cell_id` |
| Per-episode scenario | `environment_observed` events with the case and its SHA-256 `case_hash`; `EORL Episode.environmental_state_hash` |
| Every action | `EORL Event` rows with sequence number, trace/span ids and payload hash; the controller rejects edits and deletes |

## Scenario determinism

`generate_case(seed, episode, regime_shift, outcome_model)` is a pure function. The same
seed under two architectures gives byte-identical cases (paired seeds). The outcome model
`matched_v2` draws the quality inspection from the case and the chosen supplier only, so an
identical action meets an identical outcome. Runs recorded before that model existed carry
no scenario snapshot; reproduction replays them with the original `receipt_keyed_v1` draw.

## Reproducing a run

`eorl_lab.api.exports.reproduce_run(run)` (researcher role; button on the Reproducibility
page) launches a new run from the original's recorded configuration and reports whether the
scenario-hash stream and every computed metric match. This is exact for scripted and
bounded-rational runs. Language-model runs are not bit-for-bit reproducible: their
configuration, scenario stream and full trace are, and their metrics can be recomputed from
the trace.

## Exporting a run

`download_full_bundle(run)` returns a zip with the manifest (including experiment, cell,
routine, engine, outcome model, code commit, failure type and telemetry), the regenerated
scenario stream, every event as JSONL, metrics, model metadata, a requirements lock and a
README. Every analysis function in `eorl_lab.analysis` runs on that bundle without Frappe.

## Statistics

Every Analysis Plan carries `random_seed` (default 20261101), used for the permutation test
and the bootstrap interval on Hedges' g. Power planning is seeded the same way. A stored
Analysis Result records the run IDs, metric definition version, sequence scope, multiple-
testing family and statistics package version that produced it.

## The release

The submission refers to tag `orgsci-stage1-2026-11-01`. `artifact_manifest.json`, generated
by `scripts/generate_artifact_manifest.py`, records the commit, the test count and the
capabilities at that commit.
