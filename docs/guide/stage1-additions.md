# Stage 1 additions

What was added on 2026-11-01 for the *Organization Science* Stage 1 submission, and how to
use each piece. The build plan is `EORL_SUBMISSION_DAY_IMPLEMENTATION_PLAN.md` in the
repository root.

## Platform and demonstrations are separate

`EORL Experiment.experiment_type` is one of `infrastructure_validation`,
`theory_demonstration` or `empirical_study`, and `demonstration` names the demonstration an
experiment belongs to. The Lab home page lists building blocks and demonstrations
separately.

## Reusable routines

`EORL Routine Template` holds everything routine-specific: stage order, roles, handoff
keys, per-stage tools, scenario generator, terminal conditions. Two ship with the app,
Procure-to-Pay and Order-to-Cash. An architecture names its routine; the orchestrator
names none. An episode only counts as complete if the routine's terminal conditions hold.

## Actor engines

`actor_engine` (on the Experiment, or as an argument to `run_architecture`) is chosen
independently of the architecture: `scripted_deterministic`, `bounded_rational` or `llm`.
The bounded-rational engine has no language: it estimates supplier quality from its own
recalled inspections, explores 10% of the time and takes optional checks half the time,
all seeded from the scenario case. See `eorl_lab.providers.bounded_rational`.

## Matched exogenous outcomes and the supplier-quality reversal

The quality inspection is drawn from the scenario case and the chosen supplier, never from
an ERP document name, so the same action under two architectures meets the same outcome
(`outcome_model = matched_v2`). A regime shift can declare `pre_shock_latent_ground_truth`
and `post_shock_latent_ground_truth`; the demonstration reversal makes Bloomington Dairy
drop from 0.95 to 0.58 quality and Indiana Foods rise from 0.78 to 0.91 at episode 7.
Every `environment_observed` event logs the exogenous state separately.

## Registered sequence views

Every tool has a category (sense, decide, execute, verify, approve, communicate, control).
`EORL Analysis Plan.sequence_scope` names the view a process measure uses:
`all_actions` (the original definition), `consequential_actions` (no reads or control
calls; the sourcing decision tagged with the supplier), `write_actions` or
`actor_function_actions`. Scoped metrics are stored as `metric@scope`.

## New measures

- Attribute-level path coherence `path_coherence_v1`, per attribute and composite.
- Adaptive repertoire v2: observed, viable and activated-after-shock path sets, with
  utilization, retention, reuse, novelty, extinction and activation latency.
- Shock adaptation: pre-shock dominant path and supplier mix, episodes to first adaptive
  and to stable new path, performance deficit.
- Construct measures: information asymmetry, authority centralization, tool-breadth
  specialization, task-domain entropy, communication centralization. The Construct
  Registry now has a status column and more than five executable entries.

## Inference

- Hedges' g with a seeded bootstrap interval (BCa, falling back to percentile).
- Multiplicity correction (Holm, Benjamini-Hochberg, Bonferroni) across every plan that
  shares a `multiple_testing_family`, applied to each plan's primary test.
- Structured interpretation rules on the plan; every combination of significance,
  direction and equivalence maps to consistent, inconsistent, inconclusive or
  not_evaluated, and plans combine under AND, OR, weighted or separate.
- Seeded power tables for independent and paired designs, with Monte Carlo errors.

## Operations

- Queued background execution with cancellation (`eorl_lab.api.queue`).
- Failure taxonomy on runs and episodes, with a retryable flag.
- Per-call model telemetry (tokens, latency, retries) and per-run totals; an experiment
  cost estimate from completed runs.
- CSV / JSON / specification export with run, plan, scope and version metadata on the
  Process Explorer, Adaptation View, Scientific Cockpit, Power Planner and Evaluation Matrix.

## Reviewers

`/app/eorl-reviewer` is a guided walkthrough; `/app/eorl-evaluation-matrix` maps each
special-issue criterion to evidence. The reviewer role is read-only in fact: comparisons and
metrics are computed but not saved for it.
