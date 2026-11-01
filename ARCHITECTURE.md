# Architecture

EORL is one Frappe app (`eorl_lab`) on an ERPNext 14 bench. ERPNext is the environment the
actors act in; nothing in ERPNext is modified.

```text
EORL Experiment ──► run_architecture / branch_run ──► episode loop
   (design)            (eorl_lab.runtime.orchestrator)      │
                                                            ├─ routine template: stages, handoffs, tools, scenario generator
                                                            ├─ scenario generator: case = f(seed, episode, regime), hashed
                                                            ├─ per actor turn: context ─► actor engine ─► authority firewall ─► ERP tool
                                                            └─ every step ─► EORL Event (append-only, hashed)
EORL Analysis Plan ──► compare_groups ──► EORL Analysis Result (provenance, CI, adjusted p, interpretation)
                         (eorl_lab.api.analysis over pure functions in eorl_lab.analysis)
```

## Packages

| Package | Responsibility |
|---|---|
| `eorl_lab/runtime/orchestrator.py` | Runs episodes for any architecture and routine. Specialist handoff runs one actor per routine stage with logged handoffs; broad autonomy runs one actor through every stage, optionally with stage-gated tools. Records task assignments, memory, failure types and telemetry. Branching and queued runs. |
| `eorl_lab/runtime/authority.py` | The authority firewall. Called on every tool request, outside the model. |
| `eorl_lab/routines.py` | Routine templates (Procure-to-Pay, Order-to-Cash) and their seeding. |
| `eorl_lab/scenarios/` | Scenario generators. Pure functions of (seed, episode, regime, outcome model). Latent parameters never reach an actor. |
| `eorl_lab/erp/` | Semantic ERP tools: small functions that create or read real ERPNext documents through ERPNext's own mappers. |
| `eorl_lab/organization/` | Communication policy checks and the `finish_turn` control tool. |
| `eorl_lab/providers/` | Actor engines: scripted deterministic, bounded-rational, OpenAI-compatible language model. `factory.py` resolves them, including the per-run engine override. |
| `eorl_lab/memory/` | Memory backends (none, recent, episodic, semantic, procedural). |
| `eorl_lab/observability/` | Event emission, run manifests and bundles, reproduction. |
| `eorl_lab/analysis/` | Pure functions over plain data, no Frappe access: taxonomy and sequence views, paths, sequence metrics, continuity and attribute-level coherence, repertoire and adaptation, construct measures, networks, statistics, interpretation rules. Everything can run on an exported bundle. |
| `eorl_lab/api/` | Whitelisted endpoints for the Desk pages; role checks; persistence of metrics and results. |
| `eorl_lab/demonstrations/` | Setup, runs and analysis for the submission-day demonstration designs. |
| `eorl_lab/eorl_lab/doctype/` | 27 DocTypes: configuration (architecture, agents, policies, profiles, routines, grammars, constructs, regime shifts), design (experiments, analysis plans) and records (runs, episodes, events, metrics, results, branches, memory). |
| `eorl_lab/eorl_lab/page/` | 17 Desk pages, including the Reviewer walkthrough and the Evaluation Matrix. |

## Separation of concerns that the science depends on

- **Organization vs actor.** Architecture, tool policy, memory and communication are
  configuration. The actor engine is chosen separately (`actor_engine`), so the same
  organization can be run with scripted, bounded-rational or language-model actors.
- **Authority outside the model.** The model may request any tool; `authority.evaluate`
  decides what executes, from the actor's tool policy and, in the matched-tools condition,
  from the routine's current stage.
- **Exogenous vs endogenous state.** Each `environment_observed` event logs the exogenous
  state (demand, candidate suppliers, latent supplier parameters, regime) separately from
  the case. Everything else (choices, tool calls, messages, documents, memory, paths) is
  endogenous and exists only in the trace.
- **Matched outcomes.** Exogenous outcome draws depend on the scenario case and the action's
  causal input (the supplier), never on ERP document names, so the same action under two
  architectures meets the same outcome.
- **Registered views.** Process measures name their sequence scope in the Analysis Plan;
  the same events yield every view.
- **Run as the unit.** `compare_groups` refuses episode-level comparisons unless a
  mixed-effects model is declared, and verifies sibling-branch pairing before a paired test.
