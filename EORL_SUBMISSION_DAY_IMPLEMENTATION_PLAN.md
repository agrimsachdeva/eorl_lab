# EORL — Submission-Day Implementation Plan
## Everything to implement before the November 1 Organization Science Stage 1 submission

## 0. Submission logic that must govern the build

The **primary contribution is EORL**: a reusable research infrastructure for executable organizational theory.

The **agentic-routinization / adaptive-repertoire study is the first demonstration of EORL**, not the platform's defining contribution.

The final submission should therefore make the following hierarchy unmistakable:

```text
PRIMARY CONTRIBUTION
EORL: a reusable scientific instrument for organizational theory
        ↓
METHOD CAPABILITIES
Executable constructs + configurable organization + autonomous actors
+ persistent state + counterfactual histories + full observability
+ design-aware inference
        ↓
DEMONSTRATION
Agentic routinization / adaptive repertoire
        ↓
FIRST INTENDED EMPIRICAL STUDY
Specialist handoff vs broad autonomy
+ memory conditions
+ path-invalidating shock
```

Every technical feature built today should answer at least one of these questions:

1. Does this make EORL more reusable across theories?
2. Does this make an EORL result more auditable or reproducible?
3. Does this make the first theory demonstration cleaner?
4. Does this remove an obvious reviewer objection?
5. Does this help a reviewer verify the artifact quickly?

Do **not** spend time on features that are visually impressive but do not improve scientific credibility.

---

# 1. P0 — MUST IMPLEMENT TODAY

These are the highest-value changes for the Stage 1 gate.

---

## 1.1 Separate "EORL capability" from "Demonstration study" in the product itself

### Goal

A reviewer should be able to see that EORL is general infrastructure even if they ignore the agentic-routinization study.

### Implement

Add two top-level concepts in the app:

```text
EORL LAB
  ├── Constructs
  ├── Actors
  ├── Architectures
  ├── Process Grammars
  ├── Scenarios
  ├── Memory
  ├── Authority
  ├── Communication
  ├── Experiments
  ├── Runs
  ├── Analysis Plans
  └── Reproducibility

DEMONSTRATIONS
  └── Agentic Routinization / Adaptive Repertoire
```

Create a field on `EORL Experiment`:

```text
experiment_type:
  - infrastructure_validation
  - theory_demonstration
  - empirical_study
```

For the current work:

```text
scripted tests → infrastructure_validation
16-run Qwen pilot → theory_demonstration
future full P1-P3 study → empirical_study
```

### Acceptance test

A reviewer can filter the interface and clearly distinguish:

- structural validation,
- illustrative/demonstration evidence,
- actual empirical theory tests.

---

# 2. GENERALIZABILITY / REUSABLE-INFRASTRUCTURE PROOF

## 2.1 Add a second miniature organizational routine

This is one of the most valuable additions possible today.

### Why

Right now a skeptical reviewer can say:

> "This is a procurement experiment with a nice interface."

A second routine demonstrates:

> "This is a reusable organizational-process laboratory."

### Keep it deliberately small

Recommended second routine:

```text
Sales order → fulfillment → invoice → payment
```

or

```text
Expense request → approval → reimbursement
```

Prefer whichever can reuse the most existing ERPNext primitives.

### Minimum requirement

The second routine only needs:

- one process grammar,
- two or three actor roles,
- a scenario generator,
- scripted execution,
- event traces,
- one Process Explorer output.

It does **not** need an LLM experiment.

### Add a "Routine Template" abstraction

Create:

```text
EORL Routine Template
```

Fields:

```text
name
description
domain
process_grammar
required_tools
scenario_generator
terminal_conditions
default_roles
default_metrics
version
```

Current templates:

```text
Procure-to-Pay
Second Routine
```

### Acceptance test

A new experiment can choose either routine without changing the orchestrator.

---

# 3. THEORETICAL-CONSTRUCT INFRASTRUCTURE

## 3.1 Strengthen the Construct Registry

Current registry is promising but two executable measures out of eight is weak.

Implement executable definitions for at least **five** constructs before submission.

Recommended:

### Actor continuity
Already built.

### Sequential variety
Already built.

### Routine/path concentration
Already built.

### Information asymmetry

Operationalization:

```text
information_overlap(i,j)
information_visibility_by_role
```

Measure:

```text
mean pairwise Jaccard overlap of visible state variables
```

### Centralization

Operationalization:

```text
decision_rights concentration
approval_rights concentration
assignment_rights concentration
```

Measure:

```text
HHI of authority rights
```

### Specialization

Operationalization:

```text
tool/task breadth by actor
```

Measure:

```text
normalized tool breadth
task-domain entropy
```

### Optional if time: Communication centralization

Measure:

```text
network centralization from message graph
```

### Construct Registry must store

```text
construct_name
theoretical_definition
level_of_analysis
source_citations
manipulation_definition
measurement_definition
measurement_function
required_event_types
known_validity_limits
version
status
```

### Acceptance test

Reviewer opens Construct Registry and sees multiple constructs that are reusable outside the current study.

---

# 4. ATTRIBUTE-LEVEL PATH COHERENCE

## 4.1 Implement the Kim et al.-style attribute-level coherence measure

This is a high-priority scientific fix.

Current actor/stage continuity proxies are not enough.

### Represent each action/event with an attribute vector

Example:

```json
{
  "actor_role": "warehouse",
  "process_stage": "receipt",
  "object_type": "purchase_receipt",
  "supplier": "Bloomington Dairy",
  "exception_state": "quality_issue",
  "tool_family": "inspection",
  "decision_domain": "quality"
}
```

### Implement coherence at multiple levels

```text
actor coherence
role coherence
stage coherence
object coherence
supplier coherence
exception-state coherence
functional coherence
composite attribute coherence
```

### Store as versioned metric

```text
path_coherence_v1
```

### Important

Document exact computational correspondence to Kim et al. and clearly state where the implementation is an adaptation.

### Acceptance test

Process Explorer can show:

```text
actor continuity
functional continuity
attribute-level path coherence
```

separately.

---

# 5. PATH-INVALIDATING REGIME SHIFT

## 5.1 Implement a real shock that changes which path is successful

The current demand-quantity shock is insufficient.

Recommended:

### Supplier reliability / quality reversal

Pre-shock:

```text
Supplier A:
  quality = high
  reliability = high

Supplier B:
  quality = moderate
  reliability = moderate
```

Post-shock:

```text
Supplier A:
  quality = low
  reliability = low

Supplier B:
  quality = high
  reliability = high
```

The old dominant choice/path should become inferior.

### Better version

Do not make the new optimum trivial from one direct observation.

Allow agents to infer it over repeated episodes.

Example:

```text
pre:
A quality probability .95
B quality probability .78

post:
A quality probability .58
B quality probability .91
```

### Required outputs

- pre-shock dominant path,
- pre-shock supplier distribution,
- post-shock path changes,
- episodes to first adaptive path,
- episodes to stable new path,
- performance deficit,
- repertoire reuse.

### Acceptance test

The shock changes expected outcome probabilities in a way that requires behavioral adaptation.

---

# 6. ADAPTIVE REPERTOIRE IMPLEMENTATION

## 6.1 Make adaptive repertoire an actual executable construct

Define three sets:

```text
Observed paths
Viable paths
Activated-after-shock paths
```

Do not equate observed variation with viable repertoire.

### Define path viability

A path is viable if it satisfies a declared criterion such as:

```text
terminal success = true
and
no hard-policy violation
and
outcome utility >= threshold
```

### Required metrics

```text
viable_path_count
viable_path_entropy
viable_path_concentration
pre_shock_repertoire_size
pre_shock_repertoire_entropy
post_shock_reuse_rate
post_shock_novel_path_rate
path_extinction_rate
repertoire_retention
repertoire_activation_latency
```

### Recommended derived metric

```text
Adaptive Repertoire Utilization =
number of pre-shock viable paths used successfully post-shock
/
number of pre-shock viable paths
```

### Acceptance test

Adaptation View distinguishes:

- lots of paths,
- lots of viable paths,
- paths that actually help after the shock.

---

# 7. MEMORY CONDITIONS FOR THE FIRST DEMONSTRATION

## 7.1 Run at least one real memory manipulation

Current memory backends exist, but the theory needs evidence that memory is experimentally manipulable.

Minimum:

```text
Broad autonomy + no memory
Broad autonomy + episodic/procedural memory
```

Prefer matched history branches.

### Important

Use the same architecture and tools.

Only memory differs.

### Acceptance test

The manifest confirms that all non-memory configuration fields match.

---

# 8. CLEANER AUTONOMY MANIPULATION

## 8.1 Add a "matched-tools" broad-autonomy condition

Current pilot confounds:

- number of actors,
- role boundaries,
- tool breadth,
- handoffs,
- prompt wording.

Implement one additional condition that removes at least the most obvious confound.

Recommended design:

```text
Specialist Handoff
4 actors, stage-specific tools

Broad Autonomy — Matched Tool Ecology
1 actor, but tools are revealed/activated by stage
```

or alternatively:

```text
4 actors in both arms
but one architecture enforces handoff
and the other allows cross-stage continuation
```

The second is theoretically cleaner if feasible.

### Acceptance test

There is at least one comparison where actor continuity/autonomy changes without simultaneously changing every other design feature.

---

# 9. NON-LLM BASELINE

## 9.1 Promote the scripted actor into an explicit scientific baseline

Do not describe it only as a testing engine.

Create:

```text
actor_engine_type:
  - scripted_deterministic
  - llm
```

If feasible add:

```text
bounded_rational
```

A minimal bounded-rational agent can:

- choose randomly among valid options with weighted heuristics,
- have noisy information,
- use no natural-language reasoning.

### Why

This lets EORL ask:

> Does the organizational mechanism require generative semantic agents, or does the structure alone produce it?

### Acceptance test

Experiment Builder can select the actor engine independently of organizational architecture.

---

# 10. MULTIPLICITY CORRECTION

## 10.1 Implement today

This is low engineering cost and removes an easy criticism.

Support:

```text
none
holm
benjamini_hochberg
bonferroni
```

Add to `EORL Analysis Plan`:

```text
multiple_testing_family
adjustment_method
```

Add to results:

```text
raw_p
adjusted_p
family_id
```

### Acceptance test

Two or more registered outcomes can be declared as one family and adjusted automatically.

---

# 11. EFFECT-SIZE CONFIDENCE INTERVAL

## 11.1 Add confidence interval for Hedges' g

The current appendix explicitly says the pilot preregistered a g interval that the system did not compute.

Fix it.

Preferred:

```text
bootstrap CI
```

with configurable seed.

Store:

```text
effect_size
effect_size_ci_low
effect_size_ci_high
effect_size_ci_method
```

### Acceptance test

Scientific Cockpit reports:

```text
Hedges g
95% CI
```

---

# 12. REPRODUCIBLE POWER PLANNING

## 12.1 Fix Power Planner seed handling

Current UI produces slightly different Monte Carlo power estimates across clicks.

Add:

```text
simulation_seed
```

to Analysis Plan / Power Plan.

### Support

At least:

```text
independent two-group design
paired branch design
```

If paired implementation is too much today, at minimum make two-group planning deterministic.

### Display

Do not hard-code `d = .8`.

Show table:

```text
Effect / minimum meaningful effect
Runs per condition
Expected power
CI / Monte Carlo error
```

Example grid:

```text
d .3
d .5
d .8
```

### Acceptance test

Same seed and parameters return identical power estimate.

---

# 13. REVIEWER-READY ARTIFACT MODE

## 13.1 Add a "Reviewer Start Here" page

This may be one of the highest-return UI improvements.

Route:

```text
/app/eorl-reviewer
```

The page should say:

```text
EORL Reviewer Walkthrough
Approximate time: 5 minutes
```

Buttons:

### 1. Inspect an organizational architecture
Open Specialist Handoff.

### 2. Inspect one LLM run
Open a named pilot run.

### 3. Inspect one episode
Open Trace Explorer at a named episode.

### 4. Inspect the process
Open Process Explorer.

### 5. Inspect a matched branch
Open parent + child branches.

### 6. Inspect an Analysis Plan
Open a saved confirmatory plan.

### 7. Inspect the result
Open corresponding Analysis Result.

### 8. Inspect reproducibility
Open run manifest/export bundle.

### 9. Inspect Construct Registry
Show that EORL supports theory beyond the demonstration.

### Acceptance test

A person with no knowledge of the repository can understand the artifact in <5 minutes.

---

# 14. FIX REVIEWER ACCESS-CONTROL INCONSISTENCY

Current wording says reviewer is read-only but Scientific Cockpit creates Analysis Result rows.

Choose one approach.

## Preferred approach

Reviewer gets true read-only access.

Scientific Cockpit in reviewer mode:

```text
if read_only:
    compute/display result
    do not persist
```

or only open precomputed Analysis Result.

Do not let a reviewer mutate the scientific record.

### Acceptance test

EORL Viewer cannot create/update/delete any scientific record.

---

# 15. SPECIAL-ISSUE EVALUATION MATRIX

## 15.1 Add this as a front-end page and appendix table

Create:

```text
EORL Evaluation Matrix
```

Rows:

```text
Novelty
Feasibility
Auditability
Ethicality
Reproducibility
Scalability
Potential adoption
Frontier expansion
```

Columns:

```text
Criterion
EORL capability
Concrete evidence
Reviewer verification path
Known limitation
```

Examples:

### Novelty
Executable organizational counterfactuals using semantically capable actors.

### Feasibility
Live Frappe app, automated tests, LLM pilot.

### Auditability
Append-only event store + Trace Explorer.

### Ethicality
Synthetic data, no humans, authority firewall, self-hosted model.

### Reproducibility
Immutable manifests, seeds, export bundles, scripted reproduction.

### Scalability
Independent run architecture; queued execution is future limitation.

### Adoption
Open-source ERPNext, Frappe forms, pluggable routines and providers.

### Frontier expansion
Theory → executable organization → historical counterfactual → process evidence.

### Acceptance test

Every special-issue criterion has a concrete artifact and a reviewer-verification path.

---

# 16. REPOSITORY RELEASE HYGIENE

Before submission create an immutable release.

## Required

```text
README.md
QUICKSTART.md
REVIEWER_GUIDE.md
ARCHITECTURE.md
REPRODUCIBILITY.md
LIMITATIONS.md
LICENSE
CHANGELOG.md
CITATION.cff
```

Create tag:

```text
orgsci-stage1-2026-11-01
```

Record Git SHA in:

- proposal appendix,
- hosted site,
- run manifests,
- reviewer guide.

### README top section

Must answer in <30 seconds:

1. What is EORL?
2. Why does it exist?
3. What is implemented?
4. How do I run it?
5. How do I verify the submission?
6. What is the first demonstration study?

---

# 17. ARTIFACT SELF-DESCRIPTION

Add a machine-readable file:

```text
artifact_manifest.json
```

Example:

```json
{
  "name": "Executable Organizational Routine Laboratory",
  "version": "0.1-stage1",
  "commit": "...",
  "submission_date": "2026-11-01",
  "platform": "Frappe/ERPNext",
  "implemented_capabilities": [],
  "partial_capabilities": [],
  "planned_capabilities": [],
  "tests": {
    "count": 0,
    "passing": 0
  },
  "demonstrations": [
    "agentic_routinization"
  ]
}
```

This is useful for both human and machine review.

---

# 18. FIGURE / TABLE EXPORT — MINIMAL VERSION

Full builder can wait, but implement a credible minimum.

For every important page:

```text
Download CSV
Download PNG/SVG
Copy analysis specification
```

At minimum support:

- Process Explorer DFG,
- run-level comparison plot,
- adaptation trajectory,
- Analysis Result table.

Each export should contain metadata:

```text
experiment_id
analysis_plan_id
metric_version
run_ids
generated_at
```

---

# 19. PROCESS-VIEW FILTER FOR "CONSEQUENTIAL ACTIONS"

The pilot exposed an important issue: optional read-only calls changed sequence entropy.

Do not solve this by deleting reads post hoc.

Implement **multiple registered sequence views**.

Create event/action taxonomy:

```text
sense/read
communicate
decide
execute/write
verify
approve
handoff
```

Then allow Analysis Plan to specify:

```text
sequence_scope:
  - all_actions
  - consequential_actions
  - write_actions
  - actor_function_actions
```

Primary process measures must declare scope before launch.

### Why

This turns the pilot's weakness into a methodological contribution.

### Acceptance test

The same run can yield:

```text
all-action sequence
consequential-action sequence
```

without ad hoc post-processing.

---

# 20. REGISTERED INTERPRETATION RULES

Current pilot interpretation rule omitted one possible outcome.

Fix the Analysis Plan schema.

Add structured hypotheses:

```text
expected_direction
rival_prediction
support_rule
inconclusive_rule
contradiction_rule
equivalence_rule
```

For two outcomes allow:

```text
AND
OR
weighted
separate
```

Do not store interpretation only as prose.

### Acceptance test

Every possible combination of result signs/significance/equivalence maps to:

```text
consistent
inconsistent
inconclusive
not evaluated
```

without post hoc invention.

---

# 21. MATCHED SCENARIO OUTCOMES

Current pilot shared seeds but receipt quality depended partly on receipt name, so arms encountered different realized draws.

Fix this.

Outcome RNG must depend on:

```text
scenario_case_id
latent_parameter
episode_index
seed
```

and **not** on ERP document IDs.

For matched architecture comparisons:

```text
scenario outcome draw must be identical
```

unless the agent's action changes the relevant causal input.

Example:

Same supplier + same scenario case → same quality realization.

Different supplier → appropriate supplier-specific realization.

### Acceptance test

Identical action under two architectures yields identical exogenous outcome.

---

# 22. FULL EXOGENOUS / ENDOGENOUS DISTINCTION

Make scenario engine distinguish:

```text
EXOGENOUS STATE
demand
supplier latent quality
supplier latent reliability
external price
shock regime

ENDOGENOUS STATE
chosen supplier
tool calls
messages
approvals
ERP documents
memory
paths
```

Log this explicitly.

This substantially improves causal interpretability.

---

# 23. COST / RUNTIME TELEMETRY

Implement per model call:

```text
input_tokens
output_tokens
latency_ms
model
endpoint
retry_count
```

Per run:

```text
total_tokens
model_calls
wallclock_duration
estimated_cost
```

For self-hosted model:

```text
cost can be null
GPU_seconds / wallclock still recorded
```

Experiment Studio should estimate:

```text
total model calls
expected runtime
```

from pilot averages.

This directly supports scalability evaluation.

---

# 24. QUEUED EXECUTION — MINIMUM VERSION

Full distributed orchestration can wait.

But synchronous-only execution looks fragile.

If Frappe background jobs are available, implement:

```text
enqueue experiment cell/run
status:
  queued
  running
  complete
  failed
  cancelled
```

At minimum prevent the browser request from holding an entire LLM run.

### Acceptance test

Researcher can launch several runs and leave the page.

---

# 25. RUN FAILURE TAXONOMY

Create failure types:

```text
model_timeout
model_parse_error
tool_error
erp_validation_error
authority_denial_expected
authority_denial_unexpected
infrastructure_error
terminal_condition_not_met
max_turns_exceeded
```

Store:

```text
failure_type
retryable
retry_count
final_status
```

This improves auditability.

---

# 26. SECOND MODEL FAMILY — IF TIME

Only after the above.

Add an actually working second provider/model.

Could be:

```text
OpenAI-compatible endpoint #2
```

No need to implement Anthropic specifically.

Run a small robustness set:

```text
3–5 runs/condition
```

The purpose is not inference.

The purpose is to show provider/model portability.

---

# 27. FRONT-END VISUALIZATION IMPROVEMENTS — ONLY HIGH VALUE

Do not spend today on decorative visuals.

Prioritize:

## Process Explorer
- directly-follows graph
- variant table
- episode swimlane
- filter: all vs consequential actions

## Scientific Cockpit
- independent-run N
- effect + CI
- test
- equivalence
- link to run IDs
- link to Analysis Plan

## Adaptation View
- pre/post shock
- repertoire size
- path reuse
- recovery

## Construct Registry
- construct
- manipulation
- measure
- citation
- status

## Reviewer Start Here
- guided verification

These five matter more than Sankey animation.

---

# 28. DOCUMENTATION STRINGS / UI LANGUAGE

Update product language everywhere.

Avoid:

```text
simulate organization
synthetic employee
human-like agent
```

Prefer:

```text
execute organizational routine
computational actor
organizational architecture
organizational possibility structure
process performance
counterfactual history
theory demonstration
```

The theory demo should be labeled:

```text
Demonstration 1:
Agentic Routinization and Adaptive Repertoire
```

not as "the EORL theory."

---

# 29. THE MAIN SUBMISSION MUST EXPOSE THE SEPARATION

Implement the following metadata so the writing can point to real app objects.

## EORL platform contribution

Demonstrated through:
- routine templates,
- construct registry,
- experiment builder,
- persistent actors,
- authority,
- memory,
- branching,
- event sourcing,
- analysis plans,
- reviewer workflow,
- second routine.

## Theory demonstration

Demonstrated through:
- Agentic Routinization Experiment,
- P1/P2/P3,
- specialist/broad architecture,
- memory manipulation,
- shock,
- repertoire measures.

This distinction should exist in both code and documents.

---

# 30. TODAY'S PRIORITY ORDER

If time is constrained, implement in exactly this order.

## Tier 1 — highest reviewer value

1. **Matched scenario outcome fix**
2. **Consequential-action sequence scope**
3. **Path-invalidating supplier-quality shock**
4. **Adaptive repertoire executable measures**
5. **Attribute-level path coherence**
6. **Multiplicity correction**
7. **Hedges g CI**
8. **Reviewer Start Here page**
9. **Evaluation Matrix**
10. **Repository release/tag/Reviewer Guide**

## Tier 2 — proves EORL is reusable infrastructure

11. **Second miniature routine**
12. **Strengthen Construct Registry to >=5 executable constructs**
13. **Experiment type: validation/demo/study**
14. **Artifact manifest**
15. **Routine Template abstraction**

## Tier 3 — strengthens theory demonstration

16. **Memory/no-memory matched condition**
17. **Cleaner matched-tools autonomy condition**
18. **Promote scripted engine as formal non-LLM baseline**
19. **Structured interpretation rules**
20. **Run a small shock demonstration**

## Tier 4 — infrastructure maturity

21. **Queue/background execution**
22. **Failure taxonomy**
23. **Runtime/token telemetry**
24. **Export figure data/metadata**
25. **Deterministic power planner**

## Tier 5 — only if everything else is done

26. second LLM family
27. Sankey/alluvial
28. motif analysis
29. advanced sequence clustering
30. dedicated Agent/Architecture/Scenario Studio pages

---

# 31. MINIMUM NEW RUNS TO EXECUTE TODAY

Do not run a massive empirical study today.

Run enough to demonstrate instrument capability.

## A. Infrastructure validation

Scripted:

```text
5 specialist
5 broad autonomy
with matched scenario outcomes
```

Verify metrics.

## B. Memory manipulation demonstration

Prefer matched branch:

```text
5 broad + memory
5 broad + no memory
```

or fewer if expensive.

Purpose:
show the manipulation works, not claim a final theoretical result.

## C. Shock demonstration

Run:

```text
3–5 independent histories per architecture
```

with the supplier-quality reversal.

Purpose:
show post-shock paths and recovery metrics are genuinely generated.

Label explicitly:

```text
demonstration / proof of capability
not definitive theory test
```

## D. Second routine

Scripted only:

```text
1–3 runs
```

Enough to show EORL is not procure-to-pay-specific.

---

# 32. SUBMISSION-DAY ACCEPTANCE CHECKLIST

Before freezing the repo:

## EORL as infrastructure

- [ ] Separate app works on hosted site
- [ ] At least two routine templates exist
- [ ] At least five constructs have executable definitions
- [ ] Actor engine is swappable
- [ ] Organization config is separate from actor prompt
- [ ] Authority enforcement is outside model
- [ ] Memory is configurable
- [ ] Communication is configurable
- [ ] Runs are replicated and seeded
- [ ] Histories can branch
- [ ] Events are append-only
- [ ] Analysis Plans are versioned
- [ ] Reviewer workflow exists
- [ ] Evaluation Matrix exists
- [ ] Export/repro bundle works

## First theory demonstration

- [ ] Specialist and broad architectures exist
- [ ] matched exogenous scenarios work
- [ ] consequential-action sequence scope exists
- [ ] path coherence measure exists
- [ ] adaptive repertoire measures exist
- [ ] a path-invalidating shock exists
- [ ] at least one memory manipulation exists
- [ ] pilot/demo runs complete
- [ ] results clearly labeled demonstration, not final evidence

## Statistical credibility

- [ ] independent-run guardrail
- [ ] paired branch guardrail
- [ ] Welch/permutation
- [ ] effect size
- [ ] effect-size CI
- [ ] TOST
- [ ] multiplicity correction
- [ ] deterministic power seed
- [ ] metric/version provenance

## Repository

- [ ] release tag
- [ ] commit SHA recorded
- [ ] README
- [ ] QUICKSTART
- [ ] REVIEWER_GUIDE
- [ ] ARCHITECTURE
- [ ] REPRODUCIBILITY
- [ ] LIMITATIONS
- [ ] LICENSE
- [ ] CITATION.cff
- [ ] artifact_manifest.json

## Hosted site

- [ ] viewer login tested
- [ ] viewer truly read-only
- [ ] reviewer start page works
- [ ] named validation runs work
- [ ] named LLM demo runs work
- [ ] traces open
- [ ] process view opens
- [ ] analysis results open
- [ ] construct registry opens
- [ ] branch demonstration opens

---

# 33. FREEZE RULE

When the above is complete:

1. run full automated test suite;
2. record exact test count;
3. run smoke tests on hosted site;
4. create Git tag;
5. record Git SHA;
6. generate artifact manifest;
7. generate final reproduction bundle;
8. do not change scientific code after the freeze unless the tag changes;
9. update proposal and appendix only from the frozen artifact state.

The final documents must describe **exactly what exists at the frozen commit**.

---

# 34. ONE-SENTENCE BUILD TARGET

By submission time, a reviewer should be able to conclude:

> **EORL is not a procurement simulation with AI agents; it is a working, reusable laboratory in which organizational theories can be instantiated as executable structures, subjected to matched historical counterfactuals, observed as process traces, and evaluated with design-aware inference—and agentic routinization is one demonstration of what that instrument makes possible.**
