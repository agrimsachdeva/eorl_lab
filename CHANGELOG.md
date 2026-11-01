# Changelog

## 0.1-stage1 (2026-11-01), tag `orgsci-stage1-2026-11-01`

Release for the *Organization Science* special-issue Stage 1 submission. Built from
`EORL_SUBMISSION_DAY_IMPLEMENTATION_PLAN.md`; PROGRESS.md has the detailed record.

### Platform
- `EORL Routine Template` and a routine-driven orchestrator; a second routine,
  Order-to-Cash, with its own scenario generator, ERP tools and process grammar.
- Terminal conditions: an episode completes only if the routine's end state holds.
- Actor engine chosen independently of architecture (`scripted_deterministic`,
  `bounded_rational`, `llm`); new bounded-rational engine.
- Matched-tool-ecology broad autonomy (`stage_gated_tools` on EORL Architecture).
- `experiment_type` and `demonstration` on EORL Experiment; runs linked to their
  experiment and cell.
- Queued execution with cancellation; failure taxonomy; per-call model telemetry and run
  totals; experiment cost estimate.
- Run snapshots now carry resolved model, memory and tool-policy contents, the routine,
  the scenario generator, the outcome model and the code commit.

### Science
- Matched exogenous outcome model: inspection outcomes no longer depend on ERP document
  names. Older runs keep and reproduce with their original draw.
- Supplier candidates come from the scenario, so latent supplier parameters apply on any site.
- Supplier-quality reversal (path-invalidating shock) through pre/post-shock latent
  overrides; exogenous state logged separately on every episode.
- Action taxonomy and registered sequence views (`sequence_scope`).
- Attribute-level path coherence `path_coherence_v1`.
- Adaptive repertoire v2 and shock-adaptation measures; outcome utility.
- Construct Registry: status field, five newly executable constructs, four new entries.
- Recovery metrics computed on utility (metric version `v2+utility`); all other metric
  definitions unchanged (`v1`).

### Inference
- Bootstrap CI for Hedges' g; multiplicity families with Holm, Benjamini-Hochberg or
  Bonferroni; structured interpretation rules and combination rules; seeded permutation
  tests; seeded power tables for independent and paired designs.

### Reviewer access and UI
- Reviewer Start Here page and Evaluation Matrix page.
- Read-only reviewer role in fact: comparisons and metrics are not persisted for it; role
  checks on every whitelisted read endpoint; the model endpoint address hidden from it.
- Process Explorer: scope selector, variants, continuity and coherence panel. Adaptation
  View: utility, supplier, repertoire sets. Scientific Cockpit: g with CI, adjusted p,
  interpretation, scientific notation for small p. Power Planner: seeded table.
- Trace Explorer no longer marks outcome-free lifecycle events as failures.
- CSV / JSON / specification export with metadata.

### Release
- README, QUICKSTART, REVIEWER_GUIDE, ARCHITECTURE, REPRODUCIBILITY, LIMITATIONS, LICENSE,
  CITATION.cff, `artifact_manifest.json` and its generator.

## Before 0.1-stage1

Milestones 1 to 8 and SOTA Milestones 1 to 10 (2026-10-26 to 2026-10-30), and the hosted
demonstration site and language-model pilot (2026-10-31 to 2026-11-01). See PROGRESS.md.
