# Using the Front End

Open `/app/eorl-lab` on your site. The EORL Lab home page links to
every studio/monitoring page and every configuration DocType.

!!! note
    The full graphical Agent Studio, Architecture Designer, and
    Scenario Studio (spec section 28) aren't built yet. Architectures,
    agent templates, tool policies, memory profiles, and model profiles
    are composed via their ordinary DocType forms today, linked
    directly from the home page's "Configuration" section.

## Experiment Studio (`/app/eorl-experiment-studio`)

Compose architectures/agents/tool policies as DocType records first
(quick links at the top of the page), then pick a saved `EORL
Experiment` to review its summary — architecture(s), regime shift,
episode count, repetitions, cell count, total run count — and launch
it. This is "review and launch," not the full 10-step composition
wizard the spec eventually describes; that's a later milestone.

## Run Monitor (`/app/eorl-run-monitor`)

A live table of every run (auto-refreshes every 5 seconds): status,
seed, current episode, event count, start/end time, failure reason.
Click a run to open it in the Trace Explorer.

## Trace Explorer (`/app/eorl-trace-explorer`)

Pick a run, then an episode, and see its full event timeline,
filterable by event type, actor, and a "failures only" toggle. This is
the direct window into everything the event log recorded: context
built, model request/response, decision parsed, tool requested/
authorized/denied, tool result, ERP state before/after, memory query/
retrieval/write, messages sent/received. Arriving here via an episode
link from the Process Explorer or the Adaptation View pre-selects that
exact episode, not just the run.

## Compare Runs (`/app/eorl-compare-runs`)

Select several runs and compare them side by side: status, episodes,
success rate, distinct actor count, event count, and the coherence/
variety metrics (`unique_sequence_count`/path entropy, actor
continuity, average actor run length) computed from each run's actual
trace. A "Compute & Persist Full Metric Set" action runs the complete
metric suite, including post-shock adaptation metrics, for one run at
a time.

## Scientific Cockpit (`/app/eorl-scientific-cockpit`)

Pick a saved [EORL Analysis Plan](statistical-analysis.md) and two
groups of runs, then Compare. It shows KPI cards (independent-run
count vs. episode count, means, standardized effect) and a table of
both computed test families' p-values and 95% CIs, each linking
straight to its full `EORL Analysis Result` record for complete
provenance. It refuses to run if the plan's `analysis_unit` isn't
`"run"` — the independence guardrail (see
[Statistical Analysis](statistical-analysis.md)).

## Process Explorer (`/app/eorl-process-explorer`)

Pick a run. It shows the Directly-Follows Graph, pooled across every
episode in the run, as a count-sorted edge table (`from`, `to`, count,
% of that node's outgoing total) using the same canonical
`STAGE:tool_name` labels the process-mining metrics already use, plus
a per-episode swimlane table — one row per episode, one column per
step, each cell naming the actor and tool that executed it. Each
episode number in the swimlane links straight into the Trace Explorer
with that episode pre-selected: a one-click path from "what happened
in this episode's process" to "show me every event." That's linked
navigation between pages, not live multi-panel filtering where one
panel's selection re-renders another in place — see `SOTA_ROADMAP.md`'s
Milestone 10 entry for how cross-filtering was scoped.

## Network Explorer (`/app/eorl-network-explorer`)

Pick a run. It shows the agent-message network (who messaged whom, and
how often) as a simple circular-layout SVG, edge thickness proportional
to message count, plus a plain edge table underneath. A second section
lets you pick two runs and compare their networks via QAP — are they
more similar than chance, with significance from actor-label
permutation rather than an ordinary correlation test — see
[Statistical Analysis](statistical-analysis.md).

## Adaptation / Event-Study View (`/app/eorl-adaptation-view`)

Pick a run. It shows a line chart of per-episode success, plus a
phase-highlighted table calling out exactly which episode a regime
shift triggers at, if the run used one — shown here to the researcher,
never to the agents themselves. Each episode number in the table also
links into the Trace Explorer with that episode pre-selected, the same
linked-navigation pattern as the Process Explorer's swimlane above.

## Paired-Branch Inference (`/app/eorl-paired-branch-inference`)

Pick a parent run and see its branches grouped by shared
`source_episode` — the matched/paired sets a counterfactual comparison
(V2 §44.3) is allowed to treat as paired, instead of hunting for
sibling branches in the generic run list. Each group's `child_run`s
are exactly what `eorl_lab.api.analysis.compare_groups`'s own
`paired_by` sibling check accepts, so the UI's grouping and the
analysis engine's verification agree by construction.

## Theory Compiler (`/app/eorl-theory-compiler`)

A structured wizard (V2 §21), not autonomous theory generation, per
the spec's own wording. Fill in a focal theoretical construct plus the
7 other fields §21 names — theoretical definition, proposed mechanism,
manipulation, counterfactual condition, outcomes, mediating process
measures, boundary conditions — and it scaffolds a real `EORL
Experiment` + `EORL Analysis Plan` from them. `outcome_metric` is only
auto-filled when the chosen construct already has a working
measurement function (today: Routine coherence, Adaptive repertoire);
otherwise it's left as an explicit placeholder to fill in before
launching, never a guessed metric name.

## Power / Precision Planner (`/app/eorl-power-planner`)

Two simple forms, both backed by a Monte Carlo simulation of the exact
test `compare_groups` runs: given a standardized effect and N, how
much power do you have; given a target power, how many runs per group
do you need. See [Statistical Analysis](statistical-analysis.md).

## Robustness & Replication Diagnostics (`/app/eorl-robustness-diagnostics`)

Pick a saved Analysis Plan and two groups of runs. It shows a line
chart of the cumulative mean-difference estimate as runs 1..n
accumulate (replication stability), and a forest plot of the
full-sample estimate vs. re-estimating with each run excluded one at a
time (robustness). Both are diagnostics on an existing comparison, not
new confirmatory results. See [Statistical Analysis](statistical-analysis.md).

## Survival Analysis (`/app/eorl-survival-analysis`)

Pick 2 or more runs launched with a regime shift. It shows a
Kaplan-Meier curve (rendered as a line-chart approximation of the real
step function) of time-to-recovery after the shift, plus a table of
each run's own recovery time and whether it was right-censored, i.e.
never recovered within its observed episodes. See
[Statistical Analysis](statistical-analysis.md).

## Reproducibility / Export (`/app/eorl-reproducibility`)

- **Quick Export (JSON)** — a fast single-run dump.
- **Download Full Bundle (.zip)** — `run_manifest.json`,
  `architecture.json`, `resolved_agent_configs/`,
  `scenario_stream.jsonl`, `events.jsonl`, `process_paths.csv`,
  `metrics.csv`, `model_metadata.json`, `environment_metadata.json`,
  `code_commit.txt`, `requirements_lock.txt`, `README_REPRODUCE.md` —
  everything the spec's reproducibility-export section asks for except
  a multi-experiment-aware manifest, since runs aren't yet linked back
  to the experiment that launched them.
- **Reproduce & Verify** — launches a brand-new run from an existing
  run's own recorded seed/architecture/regime-shift, then verifies the
  new run's scenario-case hashes and computed metrics match. Only works
  for runs launched via the config-driven architecture entrypoint
  (`run_architecture`/`launch_pilot`); older entrypoints don't carry
  enough configuration to replay, and this reports a clear error rather
  than guessing.
