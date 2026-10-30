# Using the Front End

Open `/app/eorl-lab` on your site — the EORL Lab home page links to
every studio/monitoring page and every configuration DocType.

!!! note
    The full graphical Agent Studio, Architecture Designer, and
    Scenario Studio (spec section 28) aren't built yet. Architectures,
    agent templates, tool policies, memory profiles, and model profiles
    are composed via their ordinary DocType forms today — linked
    directly from the home page's "Configuration" section.

## Experiment Studio (`/app/eorl-experiment-studio`)

Compose architectures/agents/tool policies as DocType records first
(quick links at the top of the page), then pick a saved `EORL
Experiment` to review its summary — architecture(s), regime shift,
episode count, repetitions, cell count, total run count — and launch
it. This is "review and launch", not a from-scratch composition
wizard (that's the spec's full 10-step flow, a later milestone).

## Run Monitor (`/app/eorl-run-monitor`)

A live table of every run (auto-refreshes every 5 seconds): status,
seed, current episode, event count, start/end time, failure reason.
Click a run to open it in the Trace Explorer.

## Trace Explorer (`/app/eorl-trace-explorer`)

Pick a run, then an episode, and see its full event timeline —
filterable by event type, actor, and a "failures only" toggle. This is
the direct window into everything the event log recorded: context
built, model request/response, decision parsed, tool requested/
authorized/denied, tool result, ERP state before/after, memory query/
retrieval/write, messages sent/received.

## Compare Runs (`/app/eorl-compare-runs`)

Select several runs and compare them side by side: status, episodes,
success rate, distinct actor count, event count, and the real
coherence/variety metrics (`unique_sequence_count`/path entropy, actor
continuity, average actor run length) computed from each run's actual
trace. A "Compute & Persist Full Metric Set" action runs the complete
metric suite (including post-shock adaptation metrics) for one run at
a time.

## Reproducibility / Export (`/app/eorl-reproducibility`)

- **Quick Export (JSON)** — a fast single-run dump.
- **Download Full Bundle (.zip)** — `run_manifest.json`,
  `architecture.json`, `resolved_agent_configs/`,
  `scenario_stream.jsonl`, `events.jsonl`, `process_paths.csv`,
  `metrics.csv`, `model_metadata.json`, `environment_metadata.json`,
  `code_commit.txt`, `requirements_lock.txt`, `README_REPRODUCE.md` —
  everything the spec's reproducibility-export section asks for except
  a multi-experiment-aware manifest (runs aren't yet linked back to the
  experiment that launched them).
- **Reproduce & Verify** — launches a brand-new run from an existing
  run's own recorded seed/architecture/regime-shift, then verifies the
  new run's scenario-case hashes and computed metrics match. Only works
  for runs launched via the config-driven architecture entrypoint
  (`run_architecture`/`launch_pilot`) — older entrypoints don't carry
  enough configuration to replay, and this reports a clear error rather
  than guessing.
