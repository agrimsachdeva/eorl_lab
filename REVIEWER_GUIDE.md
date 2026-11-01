# Reviewer guide

About five minutes. Log in to the demonstration site with the reviewer account from the
submission form and open **`/app/eorl-reviewer`**. That page resolves every step below to
a real record on the site and opens it in one click. This file is the same walkthrough on
paper.

The reviewer account is read-only. It can open every EORL record and run every analysis
page, including statistical comparisons, but nothing it does is saved: comparisons are
computed and displayed without writing an Analysis Result, and metrics are computed without
writing Metric rows. It cannot open Experiment Studio, launch runs or change configuration.

## What you are looking at

The primary contribution is the instrument: a laboratory in which organizational theories
are instantiated as executable structures, run as matched counterfactual histories,
observed as process traces and evaluated with design-aware inference. *Demonstration 1:
Agentic Routinization and Adaptive Repertoire* is the first use of it. Every experiment on
the site is typed:

| Type | Meaning | On the site |
|---|---|---|
| infrastructure_validation | Checks that the instrument works. Scripted actors. | Positive control; SD-A matched outcomes; SD-D second routine |
| theory_demonstration | Shows what a theory looks like when executed. Not a test of it. | Qwen3 pilot (P1); SD-B memory; SD-C supplier reversal |
| empirical_study | A registered test of a proposition at its planned sample size. | None yet |

## The walkthrough

| Step | Open | Look for |
|---|---|---|
| 1. Architecture | An `EORL Architecture` (Specialist Handoff) | Actor slots bound to Agent Templates, each with its own tool policy, memory and model profile; the routine template |
| 2. Run | An `EORL Run` from the language-model pilot | Frozen snapshots, actor engine, routine, code commit, telemetry, failure type |
| 3. Episode | Trace Explorer at one episode | `tool_authorized` / `tool_denied` (authority is checked outside the model), `erp_mutation` events naming real ERPNext documents, payload hashes |
| 4. Process | Process Explorer for the same run | Switch scope between `all_actions` and `consequential_actions`: the same events, two registered views. Actor continuity, functional continuity and attribute-level coherence shown separately |
| 5. Branch | Paired-Branch Inference | Parent and children share history through the branch point and diverge after it |
| 6. Analysis Plan | An `EORL Analysis Plan` | `analysis_unit = run`, `sequence_scope`, equivalence bounds, multiple-testing family, structured interpretation rules |
| 7. Result | The matching `EORL Analysis Result` | Run IDs, counts, metric and package versions; raw and adjusted p; Hedges' g with its bootstrap interval; interpretation label |
| 8. Reproducibility | Reproducibility page | Manifest with code commit and scenario case hashes |
| 9. Constructs | `EORL Construct` list | The status column: which constructs are executable on recorded runs |
| 10. Adaptation | Adaptation View for an SD-C run | Supplier choice before and after the reversal, utility, observed / viable / activated repertoire |
| 11. Second routine | Process Explorer for an order-to-cash run | A different routine, roles and ERP documents through the same orchestrator |

## Evaluation matrix

Also at `/app/eorl-evaluation-matrix` with live counts from the site.

| Criterion | EORL capability | Concrete evidence | Verification path | Known limitation |
|---|---|---|---|---|
| Novelty | Theories as executable organizations acted on by semantically capable actors, with counterfactual histories | Architecture, Agent Template, Tool Policy, Routine Template; EORL Branch; actor engine independent of architecture | Steps 1, 5, 11 | One model family used so far |
| Feasibility | Working app, automated tests, scripted validation, a pre-registered model pilot | Test count in `artifact_manifest.json`; run list by actor engine | Run list | Pilot is 16 runs, one routine, one scenario |
| Auditability | Append-only events with payload hashes; authority logged outside the model; result provenance | EORL Event rejects edits and deletes; Analysis Result provenance fields | Steps 3, 7 | Immutability is enforced by the application, not the database |
| Ethicality | No human participants; synthetic data; authority firewall; self-hosted model | Demonstration site holds synthetic data only; key held in site config | Trace Explorer, `tool_denied` | Transfer to human organizations is not shown |
| Reproducibility | Frozen snapshots, seeded scenarios, matched outcome model, bundles, scripted reproduction, seeded statistics | Run manifests; `reproduce_run`; `random_seed` on plans | Step 8 | Model-driven runs are not bit-for-bit reproducible |
| Scalability | Independent runs; queued execution; per-run telemetry | `eorl_lab.api.queue`; Run telemetry fields | Run list columns | One bench, one shared ERP company, no distributed workers |
| Potential adoption | Open-source stack; configuration through forms; pluggable routines, engines, memory, providers | Two routine templates; executable constructs; OpenAI-compatible provider | Routine Template and Construct lists | No graphical designer |
| Frontier expansion | Theory to executable organization to counterfactual history to process evidence to inference | Theory Compiler; registered Analysis Plans | Steps 4 to 7 | First demonstration is illustrative, not a test |

## Reading the demonstration results

SD-B and SD-C use the **bounded-rational engine**: no language, a quality estimate from
the actor's own recalled inspections, 10% exploration and optional checks taken half the
time, all seeded from the scenario case. A difference between architectures under this
engine is produced by structure alone. In particular, the specialist Purchasing Agent never
sees the inspection result, so under specialist handoff it has no feedback from which to
learn that its supplier has become worse. That is a property of the architecture that the
instrument makes visible; it is not evidence about how language-model or human actors
behave, and these runs are labeled accordingly.
