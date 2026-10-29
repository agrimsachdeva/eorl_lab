# EORL SOTA Developer Build Specification

## Purpose

Build **EORL (Executable Organizational Routine Laboratory)** as a separate Frappe app installed on the existing ERPNext site. EORL is a scientific instrument for computational organization theory. It must allow researchers to configure organizational structures, actors, memory, information, authority, communication, tools, task allocation, environments, shocks, and experimental interventions; execute repeated organizational processes; observe every consequential action; branch matched histories into counterfactual conditions; and recover theory-facing process measures.

This is **not** a chatbot project, a generic multi-agent benchmark, or a synthetic-human simulator. The design target is:

> persistent organizational state + configurable organizational structure + autonomous computational actors + consequential action + complete observability + controlled counterfactuals + native process analysis.

The existing `erp_research` app from the prior human-AI experiment should remain intact. Create a new app (recommended name: `eorl_lab`) and reuse only low-level primitives that are genuinely generalizable.

---

# 1. Non-negotiable scientific design principles

1. **ERPNext is authoritative state.** Agents may discuss possible actions, but the organizational world changes only when an authorized ERP tool call succeeds.
2. **Organization and actor are separate layers.** Roles, permissions, approval rules, communication topology, and task assignment must not be hidden inside prompts.
3. **Action space and process path are separate.** The organization defines what can be done; agents choose what to do and in what order within the allowed space.
4. **Every theory-facing claim must be traceable to events.** No metric should exist without a raw event trail.
5. **Everything important is configurable and versioned.** Agents, models, memories, policies, architectures, scenarios, metrics, and prompts require stable IDs and versions.
6. **The same organizational history must be branchable.** Counterfactual experiments should clone a run at episode `t` and alter one theoretical condition.
7. **Replications are first-class.** A condition is not one run.
8. **LLMs are one actor engine, not the scientific ground truth.** Support deterministic, rule-based, and bounded-rational actors.
9. **The interface must be usable by a researcher without editing code.**
10. **Every feature must instantiate a construct, enable an intervention, or improve validity/auditability.**

---

# 2. Architecture decision

## Create a separate Frappe app

Recommended:

```text
apps/
  erp_research/    # existing human-AI study; leave stable
  eorl_lab/        # new reusable research infrastructure
```

Do **not** add EORL as another `ai_mode` inside the previous app.

The prior app is coupled to:
- human user sessions,
- Prolific participant identity,
- a site-wide AI condition,
- a single human-assistant chat loop,
- confirmation/rejection UX,
- Claude-specific runtime behavior.

The new app requires:
- many autonomous agents per run,
- persistent agent identity across episodes,
- separate local/shared/transactive/procedural memories,
- agent-to-agent communication,
- organizational architectures,
- authority and assignment policies,
- deterministic scenario generation,
- repeated episodes,
- environmental regimes and shocks,
- run manifests,
- counterfactual branching,
- event-sourced observability,
- process mining and theory-facing metrics.

Reuse or refactor semantic ERP primitives, not the human-experiment assumptions.

---

# 3. Five-layer EORL model

Implement EORL as five conceptually separate layers.

## 3.1 Environment

Represents the world external to the actors.

Includes:
- ERPNext persistent state,
- latent causal ground truth,
- demand,
- supplier reliability,
- supplier quality,
- delivery risk,
- price,
- inventory,
- invoice mismatch probability,
- exception distributions,
- temporal regimes,
- shocks,
- noise in observations.

The environment owns the truth. Agents receive only the observations permitted by their role/information policy.

## 3.2 Organization

Represents the arrangement within which actors operate.

Includes:
- roles,
- formal hierarchy,
- division of labor,
- decision rights,
- execution rights,
- approval rights,
- assignment rights,
- communication network,
- information boundaries,
- tool access,
- hard constraints,
- soft policies,
- escalation rules,
- goals and objective alignment,
- process grammar,
- task-assignment policy.

## 3.3 Actors

Represents computational organizational actors.

Includes:
- stable actor identity,
- model/provider,
- system prompt,
- role,
- objective,
- local memory,
- semantic memory,
- procedural memory,
- transactive memory,
- available tools,
- visible tools,
- communication rights,
- history,
- performance history,
- current assignments.

## 3.4 Process

Represents the enacted routine.

Includes:
- possible transitions,
- required states,
- hard process dependencies,
- action sequences,
- handoffs,
- messages,
- exception paths,
- actor continuity,
- path coherence,
- process variants,
- process outcomes.

## 3.5 Science

Represents experimental design and inference.

Includes:
- constructs,
- manipulations,
- factors,
- levels,
- replications,
- matched seeds,
- branch points,
- interventions,
- mechanism ablations,
- metrics,
- process mining,
- run comparison,
- reproducibility artifacts.

---

# 4. Process-control regimes

EORL must support three levels of researcher control.

## 4.1 Prescribed process

Researcher defines a tight workflow or process grammar.

Use for:
- authority experiments,
- memory experiments,
- error propagation,
- coordination under fixed process structure.

Example:
```yaml
process_mode: prescribed
required_sequence:
  - material_request
  - purchase_order
  - purchase_receipt
  - purchase_invoice
  - payment_entry
```

## 4.2 Bounded discretion — DEFAULT

Researcher defines:
- initial state,
- valid terminal state,
- hard constraints,
- role/action rights,
- process dependencies.

Agents decide:
- which tool to use,
- which actor to contact,
- sequence within valid constraints,
- whether to escalate,
- whether to search memory,
- how to handle exceptions.

Example:
```yaml
process_mode: bounded_discretion
terminal_conditions:
  invoice_paid: true
hard_constraints:
  - payment_requires_submitted_invoice
  - receipt_requires_purchase_order
  - agent_action_must_be_authorized
```

This is the default mode for the initial paper.

## 4.3 Emergent organizing

Researcher supplies:
- goals,
- resources,
- institutional constraints,
- available capabilities.

Agents can form:
- division of labor,
- informal roles,
- coordination structures,
- workflows,
- consultation networks.

Do not prioritize this for the November prototype, but architect for it.

---

# 5. Process grammar, not process script

Represent routine possibilities as a graph/grammar.

```text
Possible Process Space
        |
        +--> valid path A
        +--> valid path B
        +--> valid path C
        +--> ...
```

Distinguish:

```text
PossiblePaths ⊇ ViablePaths ⊇ ObservedPaths ⊇ RepeatedPaths
```

Support:
- legal transitions,
- illegal transitions,
- mandatory prerequisites,
- optional stages,
- alternative paths,
- exception paths,
- terminal conditions.

The process grammar should be queryable by the metrics engine.

---

# 6. Tool ecology

Agents should choose tools themselves within organizationally defined boundaries.

Separate:

```text
AllSystemTools
  ↓
RoleAuthorizedTools
  ↓
ActorVisibleTools
  ↓
ActorSelectedTool
```

Fields per tool:
- `tool_id`
- `name`
- `description`
- `semantic_category`
- `read_or_write`
- `required_role`
- `required_permission`
- `risk_level`
- `hard_preconditions`
- `cost`
- `latency`
- `discoverable`
- `version`

Support experimental manipulations of:
- tool breadth,
- tool visibility,
- tool cost,
- specialist vs broad tool access,
- discovery of previously unknown capabilities.

Later:
- tool access requests,
- delegated tool use,
- procedural composition of tools.

---

# 7. Memory as a first-class organizational variable

Implement separate memory stores.

## 7.1 Episodic memory
Actor-specific cases/events.

## 7.2 Semantic memory
Generalized propositions extracted from episodes.

## 7.3 Procedural memory
Reusable action sequences or procedures.

## 7.4 Shared organizational memory
Repository accessible to configured actors.

## 7.5 Transactive memory
Actor beliefs about who/what knows which domain.

Example:

```json
{
  "observer_actor": "buyer_1",
  "target_actor": "buyer_2",
  "domain": "supplier_delay_exception",
  "estimated_expertise": 0.78,
  "evidence_count": 6
}
```

## 7.6 Memory characteristics

All memory profiles should support:
- persistence,
- accessibility,
- retrieval strategy,
- capacity,
- decay,
- noise,
- staleness,
- write rules,
- consolidation,
- provenance.

Memory must be manipulable independently of actor model.

---

# 8. Stable actor identity and adaptation

Each actor must persist across episodes.

Required:
- stable `actor_id`,
- role history,
- memory history,
- message history,
- assignments,
- performance history,
- relationship history,
- tool-use history.

Do not recreate a fresh actor each episode.

Allow actor behavior to change through:
- memory,
- learned procedures,
- beliefs,
- relationships,
- role changes,
- tool access,
- assignment history.

Do not require model weight updates.

---

# 9. Communication as organization

Represent communication topology explicitly.

Create `Communication Policy` / `Communication Graph`.

Support:
- hierarchy,
- fully connected,
- functional silos,
- team networks,
- hub-and-spoke,
- brokered communication,
- temporary project channels.

Edge attributes:
- allowed/blocked,
- latency,
- cost,
- bandwidth,
- reliability,
- visibility/privacy,
- message limit.

Agents choose whether and whom to contact within the graph.

Every message must be logged.

---

# 10. Consultation and expertise coordination

Actors should choose among:

```text
solve_alone
search_local_memory
search_shared_memory
consult_peer
ask_manager
escalate
delegate
request_tool_access
```

Do not hard-code who is expert.

Let expertise emerge from repeated task exposure and performance.

Track:
- consultation network,
- advice centrality,
- successful referrals,
- expertise beliefs,
- expertise accuracy.

---

# 11. Task allocation layer

Task assignment must be configurable.

Policies:
- random,
- round_robin,
- manager_assigned,
- workload_balancing,
- current_performance,
- expertise_matching,
- self_selection,
- bidding/auction,
- developmental/experience_balancing.

This enables:

```text
Allocation_t
  → Experience_t
  → Expertise_t+1
  → Allocation_t+1
```

Store each assignment decision and its rationale/policy.

---

# 12. Authority model

Do not model authority as one permission flag.

Separate:

1. **Execution authority** — may perform action.
2. **Decision authority** — may choose course of action.
3. **Approval authority** — may authorize another actor's action.
4. **Assignment authority** — may allocate work.

Possible future additions:
- veto authority,
- escalation authority,
- exception authority.

Represent authority in structured policy objects, not only prompts.

---

# 13. Hard constraints vs soft organizational rules

## Hard constraints
System rejects violation.

Examples:
- payment without submitted invoice,
- receipt without PO,
- unauthorized DocType write.

## Soft rules
Actor can violate; violation is logged and consequences may follow.

Examples:
- purchases > $10K should have manager approval,
- supplier-quality exception should be escalated,
- quote comparison recommended before selection.

This distinction is essential for future studies of compliance, workaround, governance, and rule enactment.

---

# 14. Formal goals and incentives

Avoid personality-like constructs unless theory requires them.

Represent formal objectives:

```yaml
buyer:
  objectives:
    cost: 0.5
    delivery_reliability: 0.3
    quality: 0.2

warehouse:
  objectives:
    stockout_avoidance: 0.7
    inventory_cost: 0.3

finance:
  objectives:
    cash_preservation: 0.5
    payment_timeliness: 0.5
```

Support:
- local vs global goal weights,
- goal conflict,
- aligned vs misaligned incentives.

---

# 15. Scenario engine with latent causal ground truth

The scenario generator must generate structured state, not prose only.

Example:

```json
{
  "scenario_id": "S-00124",
  "latent": {
    "supplier_A_reliability": 0.91,
    "supplier_B_reliability": 0.62,
    "supplier_A_quality": 0.70,
    "supplier_B_quality": 0.93,
    "demand_level": 1200,
    "invoice_error_prob": 0.08
  },
  "observations": {
    "buyer": {...},
    "warehouse": {...},
    "finance": {...}
  }
}
```

The environment determines outcomes from latent variables plus controlled randomness.

Agents do not see latent ground truth unless the information policy permits it.

---

# 16. Environmental regimes and shocks

Support:

- stable regime,
- sudden regime shift,
- gradual drift,
- recurring/cyclical change,
- rare extreme event,
- adversarial disturbance.

A `Regime` object should define scenario distributions for an episode range.

Example:

```yaml
regimes:
  - name: stable
    start_episode: 1
    end_episode: 100
  - name: supplier_reversal
    start_episode: 101
    end_episode: 160
    changes:
      supplier_A_reliability: 0.55
      supplier_B_reliability: 0.90
```

---

# 17. Counterfactual history branching

This is a flagship capability.

At episode `t`, clone:

- ERP state,
- actor memories,
- communication network,
- performance history,
- assignments,
- organizational state,
- scenario RNG state.

Then create branches.

```text
history 1..75
    |
    +-- branch A: specialist architecture
    +-- branch B: broader autonomy
    +-- branch C: shared memory
```

Requirement:

```text
History_A[1:75] == History_B[1:75] == History_C[1:75]
```

Only the intervention differs after the branch.

Expose branch creation in the UI.

---

# 18. Deterministic replay vs stochastic actors

Preserve:
- run config,
- seeds,
- prompt versions,
- model identifiers,
- tool versions,
- prior states,
- event ordering.

Do not promise bit-identical LLM outputs.

Instead:
- enable best-effort replay,
- persist raw responses,
- use multiple replications,
- support deterministic baselines.

---

# 19. Mechanism-ablation engine

The experiment layer must support targeted ablations.

Example theory:

```text
Autonomy
  → Actor Continuity
  → Path Coherence
  → Adaptive Repertoire
  → Adaptation
```

Possible ablations:
- autonomy ON, memory OFF,
- autonomy ON, procedural memory randomized,
- actor continuity fixed, tool breadth changed,
- communication removed,
- task assignment held constant,
- shared memory replaced with local memory.

Provide an interface for marking a run as an ablation of another configuration.

---

# 20. Construct Registry

Create a reusable library connecting theory to implementation.

`EORL Construct` fields:

- `construct_name`
- `theoretical_definition`
- `level_of_analysis`
- `source_citations`
- `computational_definition`
- `manipulation_strategy`
- `measurement_function`
- `required_events`
- `validity_notes`
- `version`

Initial constructs:

### Centralization
Manipulation:
- concentration of decision/assignment/approval rights.

Measures:
- authority HHI,
- decision centrality.

### Specialization
Manipulation:
- breadth of authorized task/tool domains.

Measures:
- actor task entropy,
- tool breadth.

### Formalization
Manipulation:
- number/strength of hard and soft process rules.

### Information asymmetry
Manipulation:
- overlap in actor observation sets.

### Hierarchy
Manipulation:
- approval/assignment depth.

### Transactive memory
Measures:
- accuracy of beliefs about expertise location,
- sharedness,
- consultation success.

### Routine coherence
Measures:
- actor continuity,
- situational attribute persistence,
- path persistence.

### Adaptive repertoire
Measures:
- diversity of viable prior paths,
- usable alternatives after regime shift,
- recombination rate,
- post-shift path activation.

---

# 21. Theory-to-experiment workflow ("Theory Compiler")

Do not attempt fully autonomous theory generation.

Build a structured wizard.

Researcher enters:

1. focal theoretical construct,
2. theoretical definition,
3. proposed mechanism,
4. manipulation,
5. counterfactual condition,
6. outcomes,
7. mediating process measures,
8. boundary conditions.

System produces:
- architecture configuration,
- scenario requirements,
- metric list,
- event requirements,
- run design.

Example:

```text
Theory: Centralization improves coordination but may reduce search breadth.
Manipulation: assignment + approval authority concentrated in manager agent.
Counterfactual: decentralized peer assignment.
Outcome: coordination errors, search breadth, adaptation.
```

Store the mapping as part of the experiment manifest.

---

# 22. Native process-mining layer

Every run should automatically support:

- directly-follows graph,
- process variants,
- transition matrix,
- sequence entropy,
- Levenshtein/optimal matching distance,
- path coherence,
- actor continuity,
- role switching,
- handoff matrix,
- temporal motifs,
- exception paths,
- medoid trajectories,
- path concentration,
- stage transition rates,
- pre/post-regime comparisons.

Do not make process mining an external afterthought.

Create metrics from raw event data, not from LLM summaries.

---

# 23. Endogenous network layer

Maintain longitudinal networks:

```text
CommunicationGraph_t
AdviceGraph_t
DelegationGraph_t
ApprovalGraph_t
ExpertiseBeliefGraph_t
```

Store edges as events and materialized snapshots.

Possible edge attributes:
- frequency,
- success,
- latency,
- trust proxy (behavioral only),
- expertise belief,
- referral count.

Avoid psychological interpretation unless behaviorally grounded.

---

# 24. Actor engines

Implement provider abstraction.

Minimum:

```text
LLMProvider
DeterministicRuleProvider
RandomBaselineProvider
BoundedRationalProvider
```

LLM providers:
- Anthropic,
- OpenAI,
- local/open-weight endpoint.

All provider outputs should normalize to a structured decision schema.

Example:

```json
{
  "decision_type": "tool_request",
  "goal": "resolve supplier delay",
  "target": "Purchase Order PUR-ORD-...",
  "tool_name": "get_supplier_history",
  "tool_input": {...},
  "message_target": null,
  "confidence": 0.71,
  "public_rationale": "Need historical delivery performance before selecting supplier."
}
```

Do not store private chain-of-thought. Store only a concise decision rationale appropriate for audit.

---

# 25. Authority firewall

Every write/action passes through:

```text
Agent Request
  ↓
Role Policy
  ↓
Tool Policy
  ↓
Object Preconditions
  ↓
Process Hard Constraints
  ↓
Approval Requirements
  ↓
Execute / Reject / Route for Approval
```

Log each step.

Policy output:

```json
{
  "allowed": false,
  "reason": "requires_manager_approval",
  "next_required_actor": "purchasing_manager"
}
```

---

# 26. Observability and event sourcing

Canonical event envelope:

```json
{
  "event_id": "...",
  "timestamp": "...",
  "run_id": "...",
  "branch_id": "...",
  "episode_id": "...",
  "turn_id": "...",
  "actor_id": "...",
  "event_type": "...",
  "scenario_id": "...",
  "payload": {...},
  "code_version": "...",
  "config_version": "..."
}
```

Required events:

```text
run_started
run_branched
episode_started
scenario_sampled
observation_created
actor_turn_started
memory_query
memory_retrieved
message_sent
message_received
task_assigned
decision_created
tool_discovered
tool_requested
policy_check
approval_requested
approval_decision
tool_executed
erp_state_before
erp_state_after
memory_written
metric_snapshot
episode_outcome
episode_ended
run_ended
```

Every derived metric must identify the raw event range it uses.

---

# 27. Reproducibility manifest

Each run manifest must contain:

- experiment ID/version,
- architecture ID/version,
- actor profile IDs/versions,
- memory profile IDs/versions,
- tool-policy versions,
- communication-policy version,
- assignment-policy version,
- process grammar version,
- scenario generator version,
- regime definition,
- seeds,
- model/provider identifiers,
- prompts/system instructions hashes,
- code Git SHA,
- ERP fixture/snapshot version,
- metric package version,
- created timestamp,
- parent branch/run if any.

---

# 28. Front-end modules

## 28.1 Lab Home
Cards:
- Experiments
- Runs
- Agents
- Architectures
- Scenarios
- Regimes
- Construct Registry
- Trace Explorer
- Metrics
- Reproducibility

## 28.2 Agent Studio
Configure:
- actor identity,
- role,
- provider/model,
- prompt profile,
- goals,
- memory,
- tools,
- communication,
- authority.

Actions:
- clone,
- version,
- validate,
- test single turn.

## 28.3 Architecture Designer
Graphical nodes/edges.

Nodes = actors/roles.
Edges = communication/authority/delegation.

Side panels:
- tool access,
- information access,
- task domains,
- approval chains.

## 28.4 Process Grammar Designer
Display states/transitions.

Allow:
- required,
- optional,
- prohibited transitions,
- hard prerequisites,
- terminal conditions.

## 28.5 Scenario Studio
Build:
- latent variables,
- distributions,
- observations,
- exception classes,
- outcome logic.

Preview generated scenarios.

## 28.6 Regime / Shock Studio
Define:
- episode ranges,
- changed distributions,
- one-time shocks,
- drift functions.

## 28.7 Experiment Builder
Select:
- process mode,
- architecture(s),
- actor profile(s),
- scenario,
- regime,
- factors/levels,
- replications,
- seeds,
- metrics,
- branch points,
- ablations.

Show:
- total runs,
- total episodes,
- estimated token/model calls,
- estimated cost if possible.

## 28.8 Run Monitor
Show:
- queue,
- active run,
- episode,
- actor currently acting,
- tool calls,
- errors,
- cost/token counts,
- state summary.

Controls:
- pause,
- resume,
- cancel,
- branch,
- replay.

## 28.9 Trace Explorer
Timeline view.

For each event:
- actor,
- observation,
- memory,
- messages,
- decision,
- authorization,
- ERP action,
- before/after state.

Filter by:
- actor,
- event type,
- ERP object,
- process stage,
- exception type.

## 28.10 Process Explorer
Show:
- directly-follows graph,
- variants,
- actor paths,
- handoffs,
- entropy,
- path coherence,
- pre/post shock paths.

## 28.11 Run Comparison
Compare conditions:
- performance,
- variety,
- coherence,
- repertoire,
- adaptation,
- network structure.

## 28.12 Reproducibility Export
Generate ZIP:
- manifest,
- configs,
- JSONL traces,
- Parquet tables,
- metric outputs,
- analysis metadata,
- README.

---

# 29. Frappe DocTypes

Minimum recommended DocTypes:

```text
EORL Agent Profile
EORL Prompt Profile
EORL Memory Profile
EORL Tool
EORL Tool Policy
EORL Communication Policy
EORL Authority Policy
EORL Assignment Policy
EORL Process Grammar
EORL Architecture
EORL Construct
EORL Scenario Template
EORL Regime
EORL Experiment
EORL Experiment Factor
EORL Run
EORL Run Manifest
EORL Branch
EORL Episode
EORL Actor State
EORL Task Assignment
EORL Event
EORL Metric Definition
EORL Metric Result
EORL Reproducibility Bundle
```

Use child tables only where appropriate. High-volume event data may eventually need an optimized external/event store, but begin with Frappe tables if performance is sufficient.

---

# 30. Suggested Python module layout

```text
eorl_lab/
  eorl_lab/
    api/
      experiments.py
      runs.py
      traces.py
      configs.py
    actors/
      base.py
      runtime.py
      providers/
        anthropic.py
        openai.py
        local.py
        deterministic.py
        bounded_rational.py
    organization/
      authority.py
      communication.py
      assignment.py
      tool_ecology.py
      goals.py
    process/
      grammar.py
      state_machine.py
      path_extraction.py
    memory/
      episodic.py
      semantic.py
      procedural.py
      shared.py
      transactive.py
    environment/
      scenario.py
      regimes.py
      outcomes.py
      observations.py
    erp/
      adapter.py
      tools/
        search.py
        reports.py
        purchase.py
        stock.py
        accounting.py
    experiments/
      orchestrator.py
      branching.py
      ablation.py
      replication.py
    observability/
      events.py
      manifests.py
      replay.py
    metrics/
      process.py
      network.py
      performance.py
      adaptation.py
    export/
      bundle.py
      parquet.py
      jsonl.py
    pages/
      ...
```

---

# 31. Scientific acceptance tests

A feature is not done because the UI renders.

## 31.1 Run reproducibility test
Two runs with deterministic actor provider and identical manifest must produce identical event streams.

## 31.2 Matched scenario test
Different architectures with same scenario seed must receive identical environmental scenarios.

## 31.3 Permission test
Unauthorized action must be rejected regardless of model instruction.

## 31.4 Memory isolation test
Local memory of actor A must not appear to actor B unless explicitly shared.

## 31.5 Branch test
Two child branches must have byte-equivalent/logically identical history through the branch point.

## 31.6 Trace reconstruction test
Given an episode ID, system must reconstruct:
- observations,
- messages,
- decisions,
- actions,
- ERP mutations,
- outcome.

## 31.7 Metric provenance test
Every metric result must reference:
- metric version,
- run,
- event range/input table.

## 31.8 Provider swap test
Same experiment can be executed with another provider without changing organization configuration.

---

# 32. November deadline priorities

## P0 — MUST BE SOLID

1. separate `eorl_lab` app;
2. semantic ERP adapter;
3. persistent actor profiles;
4. provider abstraction;
5. four role-bounded agents;
6. bounded-discretion process mode;
7. tool-policy / authority firewall;
8. local persistent memory;
9. agent-to-agent messaging;
10. deterministic scenario engine with latent ground truth;
11. specialist vs broad-autonomy architecture configurations;
12. repeated episodes;
13. stable regime + one controlled regime shift;
14. event sourcing;
15. immutable run manifest;
16. process path extraction;
17. core measures:
   - actor continuity,
   - handoffs,
   - sequential variety,
   - path concentration,
   - path coherence,
   - outcome performance,
   - post-shift recovery;
18. Trace Explorer;
19. Experiment Builder;
20. exportable raw traces.

## P1 — STRONGLY DESIRABLE

1. shared/procedural memory profiles;
2. configurable communication graph;
3. task assignment policies;
4. experiment replications from UI;
5. branch-at-episode counterfactual cloning;
6. mechanism-ablation support;
7. deterministic non-LLM provider;
8. run comparison dashboard;
9. process explorer;
10. JSONL + Parquet export;
11. basic Construct Registry.

## P2 — POST-SUBMISSION RESEARCH FRONTIER

1. transactive memory;
2. semantic memory consolidation;
3. memory decay/staleness;
4. dynamic tool discovery/access requests;
5. endogenous informal role formation;
6. self-organized division of labor;
7. soft-rule violation studies;
8. incentive misalignment;
9. endogenous network evolution;
10. full Theory Compiler wizard;
11. gradual drift/cyclical/adversarial regimes;
12. HPC distributed runner;
13. model-family experiment sweeps;
14. advanced optimal matching / motif discovery;
15. reusable public construct library.

---

# 33. Initial paper configuration

## Focal theory
Agentic routinization and adaptive repertoire.

## Process mode
`bounded_discretion`

## Routine
Procure-to-pay.

## Actors
- Buyer / Purchasing Agent
- Purchasing Manager
- Warehouse / Receiving Agent
- Accounts Payable Agent

## Architecture A
Specialist / handoff-intensive.

## Architecture B
Broader autonomy / actor-continuous.

## Environment
Stable episodes followed by controlled supplier/exception regime shift.

## Primary mechanism
```text
Agent autonomy
  → actor continuity
  → path coherence / process variety
  → adaptive repertoire
  → post-shift adaptation
```

## Rival mechanism
Autonomy expands path repertoire through memory and capability recombination.

## Required ablations
At minimum:
- broad autonomy + persistent memory,
- broad autonomy + memory reset,
- specialist + persistent memory.

Optional:
- broad autonomy + narrow tool visibility,
- broad autonomy + restricted communication.

---

# 34. Developer workflow

For every new module:

1. define scientific requirement;
2. define configuration schema;
3. define event schema;
4. implement service;
5. expose API;
6. expose front-end configuration;
7. write deterministic test;
8. write integration test;
9. confirm event trace;
10. confirm export/replay;
11. update versioned manifest.

Do not add hidden defaults that alter experimental meaning.

All defaults must be visible in the run manifest.

---

# 35. Definition of done for EORL v1

A researcher can:

1. open EORL in ERPNext;
2. define or clone four agents;
3. assign roles, memory, tools, and authority;
4. choose specialist or broad-autonomy architecture;
5. choose the procurement scenario and regime shift;
6. choose number of replications and seeds;
7. launch the experiment without editing code;
8. observe the runs;
9. open any episode and reconstruct what happened;
10. compare process paths and adaptation across conditions;
11. export raw events and metrics;
12. reproduce a deterministic baseline run;
13. branch a run at a selected episode if P1 branching is complete.

That is the minimum credible scientific laboratory.

---

# 36. Final product principle

EORL should not compete with generic agent-society frameworks on the number of agents or breadth of simulated social life.

Its niche is narrower and stronger:

> **EORL is a laboratory for executable organizing: persistent enterprise state, consequential action, explicit organizational structure, configurable process discretion, longitudinal memory, native process traces, matched-history counterfactuals, and theory-linked experimental constructs.**

Build for that claim.

---

# 37. Scientific Visualization and Statistical Workbench

The EORL front end must not stop at experiment configuration and trace inspection. It should function as an integrated **scientific workbench** that moves from design to execution to visualization to inference while preserving full provenance.

The core requirement is:

> **Every visualization and inferential result must know which experiment design, run manifest, analysis unit, event subset, metric version, and statistical specification produced it.**

Do not create a generic dashboard layer disconnected from the experiment model.

## 37.1 Workspace hierarchy

The user should be able to move through four levels without losing context:

```text
Experiment
  → Condition / Branch
    → Run
      → Episode
        → Event / ERP object
```

At every level, the interface should show:
- current filters,
- number of independent runs,
- number of episodes,
- regime,
- branch,
- provider/model strata,
- exclusions,
- metric version,
- analysis-plan version.

---

# 38. Experiment Overview ("Scientific Cockpit")

Create an experiment-level dashboard with synchronized panels.

## 38.1 Header / controls

Display:
- Experiment name/version
- Theory / construct being tested
- Conditions
- Factor levels
- Regime / shock
- Replications per condition
- Completed / failed / retried runs
- Current analysis unit
- Analysis plan version
- Model/provider filters
- Seed filters
- Metric set
- Branch selection
- Pre/post period selection

## 38.2 Primary KPI cards

These should not be vanity metrics. Show theory-relevant summaries such as:
- outcome performance,
- path coherence,
- sequential variety,
- actor continuity,
- handoff rate,
- dominant-path share,
- adaptive repertoire,
- recovery time,
- exception-resolution rate.

Each card should show:
- estimate,
- uncertainty,
- comparison condition,
- sample size at the **independent-run level**,
- click-through to distribution and test.

## 38.3 Linked selections

Selecting a condition, path, agent, regime, or time interval in one visualization should filter the others.

Example:
- click a post-shock path in the process map;
- show only runs containing that path;
- update outcome distribution;
- update actor/network view;
- update episode table;
- allow drilldown to traces.

---

# 39. Process Visualization Suite

Implement multiple process views because no single representation captures routine dynamics.

## 39.1 Directly-Follows Graph (DFG)

Nodes = process/action states.
Edges = directly-following transitions.

Controls:
- condition,
- regime,
- actor,
- process stage,
- exception type,
- minimum edge frequency,
- normalize by run vs episode.

Overlays:
- edge frequency,
- median latency,
- success rate,
- dominant actor,
- pre/post change.

Click edge to list contributing episodes.

## 39.2 Process variant explorer

Table + visual path representation.

Columns:
- variant ID,
- sequence,
- frequency,
- condition share,
- success,
- average cost/time,
- pre/post regime,
- first appearance episode,
- last appearance episode.

Support:
- modal path,
- medoid path,
- novel post-shock paths,
- disappearing paths,
- persistent paths.

## 39.3 Sankey / alluvial view

Use for:
- actor handoffs,
- process stages,
- condition → path → outcome,
- pre-shock path → post-shock path.

Must support filtering and aggregation; do not render unreadable thousands of paths.

## 39.4 Swimlane episode timeline

Lanes:
- actor,
- ERP/system,
- shared memory if useful.

Events:
- observe,
- retrieve memory,
- message,
- decide,
- request tool,
- approval,
- execute,
- verify,
- outcome.

Click event to open:
- visible observation,
- decision artifact,
- memory retrieval,
- policy result,
- ERP state before/after,
- linked messages.

## 39.5 Sequence similarity and clustering

Views:
- pairwise distance heatmap,
- cluster membership,
- medoid sequence,
- cluster size,
- cluster-by-condition composition.

Methods may include:
- optimal matching,
- edit distance,
- transition-based distances,
- motif-derived features.

Do not cluster by default without showing method and parameters.

## 39.6 Repertoire explorer

For adaptive-repertoire theory, show:
- cumulative unique viable paths over episodes,
- path discovery rate,
- path reuse rate,
- pre-shock repertoire,
- post-shock activation of prior paths,
- genuinely new post-shock paths,
- obsolete paths,
- repertoire concentration.

Support a "path genealogy" view showing when paths first emerged and whether they were later reused.

---

# 40. Longitudinal and Shock Visualization

The first paper depends on temporal adaptation. Make shock analysis first-class.

## 40.1 Adaptation trajectory

Plot per condition:
- episode index relative to shock,
- outcome performance,
- path coherence,
- variety,
- repertoire,
- error rate.

Show:
- mean/median across independent runs,
- 95% CI,
- shock marker,
- pre-specified pre/post windows.

## 40.2 Event-study view

For a shock at episode 0, show estimated condition differences at:

```text
-10, -9, ... -1, 0, +1, ... +20
```

Useful for:
- checking pre-shock equivalence,
- visualizing divergence,
- recovery.

## 40.3 Recovery metrics

Expose:
- immediate performance loss,
- time to 50% recovery,
- time to full recovery,
- area under performance deficit,
- new-path activation latency,
- stabilization time.

## 40.4 Change-point diagnostics

Optional advanced view:
- observed trajectory,
- detected change point,
- declared shock,
- discrepancy between them.

This can reveal endogenous organizational disruption not perfectly aligned with the imposed environmental change.

---

# 41. Distribution and Effect Visualization

Every aggregate comparison should expose the underlying run-level distribution.

Implement:
- box/violin/raincloud-style distributions,
- ECDF,
- dot/strip plots for modest run counts,
- paired slope plots for matched branches,
- forest plots for effect sizes,
- coefficient plots for regression/mixed models,
- interaction plots,
- marginal-effect plots.

Never show only a bar with a p-value.

Default display:
- raw run-level observations when feasible,
- effect size,
- 95% CI,
- independent-run `n`.

---

# 42. Network Visualization

Networks are first-class organizational outcomes.

Views:

## 42.1 Communication network
Edges = messages.

## 42.2 Consultation network
Edges = requests for help / expertise.

## 42.3 Delegation network
Edges = delegated work.

## 42.4 Approval network
Edges = approval requests/decisions.

## 42.5 Expertise-belief network
Edges = actor belief that another actor is knowledgeable in domain `d`.

Controls:
- condition,
- regime,
- episode range,
- domain,
- edge threshold.

Metrics:
- degree,
- betweenness,
- density,
- centralization,
- reciprocity,
- modularity,
- concentration.

Show network evolution over time, not only one pooled graph.

---

# 43. Mechanism and Ablation Dashboard

A theory-building system should visually compare mechanisms.

For a declared mechanism:

```text
Autonomy
  → Actor Continuity
  → Path Coherence
  → Adaptive Repertoire
  → Adaptation
```

Show:
- each link's estimated effect,
- confidence interval,
- ablation condition,
- whether the pattern survives provider/model changes,
- whether a simpler non-LLM actor reproduces it.

Ablation matrix example:

| Condition | Autonomy | Persistent Memory | Broad Tools | Communication | Outcome |
|---|---:|---:|---:|---:|---:|
| Base specialist | low | yes | no | yes | ... |
| Broad autonomy | high | yes | yes | yes | ... |
| Memory ablation | high | no | yes | yes | ... |
| Tool ablation | high | yes | no | yes | ... |
| Comm ablation | high | yes | yes | no | ... |

The interface should make it easy to determine which component is necessary for the observed macro pattern.

---

# 44. Design-Aware Statistical Inference Engine

Do **not** implement a generic "Run significance test" button that treats all rows as independent.

The statistical engine must read the experiment design and require an explicit analysis specification.

## 44.1 Analysis Specification object

Create `EORL Analysis Plan`.

Fields:

```text
analysis_plan_id
experiment_id
version
research_question
estimand
outcome_metric
factor(s)
contrast
analysis_unit
cluster_unit
paired_by
time_window
regime
model_family
formula
covariates
multiple_testing_family
alpha
equivalence_bounds
bootstrap_iterations
permutation_iterations
exclusion_rule
created_by
created_at
```

The plan should be saved before inferential results are generated.

## 44.2 Independence guardrail

Default principle:

> Episodes inside one run are **not** independent replications.

If one simulated organization experiences 150 episodes, that is not `n=150` for a between-architecture hypothesis.

For between-condition inference, the default independent unit should be the independently seeded **run / organizational history**.

Episodes may be modeled using:
- mixed-effects models,
- GEE,
- cluster-robust SEs,
- run fixed effects,
- other declared longitudinal models.

The UI must prominently display:
- `N independent runs`,
- `N episodes`,
- clustering structure.

## 44.3 Paired counterfactual branches

If two branches share identical history until episode `t`, treat them as paired/matched.

Support:
- paired t-test,
- Wilcoxon signed-rank,
- paired permutation test,
- paired effect sizes,
- branch-pair fixed effects.

Do not treat the branches as unrelated independent histories.

## 44.4 Recommended test families

The system may **recommend**, but should never silently select, the test.

### Two independent conditions
Potential:
- Welch t-test,
- permutation test,
- Mann-Whitney as robustness.

Report:
- mean/median difference,
- Hedges g or standardized effect,
- 95% CI.

### Paired branch comparison
Potential:
- paired t-test,
- paired permutation,
- Wilcoxon signed-rank.

### More than two conditions
Potential:
- linear model / ANOVA,
- Welch ANOVA,
- permutation omnibus,
- planned contrasts.

Avoid a long series of uncorrected pairwise tests.

### Factorial designs
Use:
- linear model,
- GLM,
- mixed model where required.

Expose:
- main effects,
- interactions,
- marginal effects,
- coefficient plot.

### Binary outcomes
Use:
- logistic regression,
- mixed-effects logistic model,
- Fisher exact for small independent samples where appropriate.

### Count outcomes
Use:
- Poisson / negative-binomial models,
- mixed variants where nested.

### Repeated longitudinal episodes
Use:
- mixed-effects regression,
- GEE,
- segmented regression,
- event-study models.

### Time to recovery / completion
Use:
- survival analysis,
- Kaplan-Meier visualization,
- Cox model or alternative when assumptions are reasonable.

### Process-distribution differences
Support:
- permutation tests on entropy,
- bootstrap CI for path concentration,
- Jensen-Shannon distance,
- sequence-distance summaries.

### Network comparisons
Prefer run-level network metrics for ordinary comparisons.

Advanced:
- QAP/MRQAP for relational hypotheses,
- permutation-based network comparisons.

Do not treat edges as independent observations.

---

# 45. Effect Sizes, Uncertainty, and Equivalence

Every inferential comparison should prioritize magnitude and uncertainty.

Always provide where applicable:
- raw effect,
- standardized effect,
- 95% CI,
- p-value,
- adjusted p/q-value,
- independent-run sample size.

Support:
- Hedges g,
- Cohen d,
- odds ratio,
- rate ratio,
- risk difference,
- standardized coefficients,
- partial R² / model R²,
- bootstrap differences.

## 45.1 Equivalence testing

Add TOST / equivalence testing.

This is especially important when a theory predicts that two architectures yield comparable performance but differ in process structure.

The researcher must declare equivalence bounds **before** running the test.

## 45.2 Noninferiority

Optional but useful for hypotheses such as:
- broad autonomy preserves performance while changing process structure.

Again, bounds must be declared in the Analysis Plan.

---

# 46. Multiple Testing and Researcher Degrees of Freedom

Support:
- Benjamini-Hochberg FDR,
- Holm correction,
- Bonferroni only when explicitly desired.

The Analysis Plan should define families of tests.

Log:
- all tested outcomes,
- all contrasts,
- exclusions,
- transformations,
- model specifications.

Do not allow hidden post hoc switching without creating a new analysis-plan version.

---

# 47. Robustness and Sensitivity Workbench

Create a robustness panel.

Rows may include:
- primary specification,
- alternative metric definition,
- alternative post-shock window,
- alternative provider/model,
- deterministic baseline,
- memory ablation,
- prompt version,
- excluded failed runs,
- all runs,
- nonparametric/permutation alternative.

Columns:
- effect estimate,
- CI,
- p/q,
- sample size,
- result direction.

Provide a forest plot across specifications.

This makes computational robustness visible rather than buried in appendices.

---

# 48. Replication and Monte Carlo Diagnostics

The UI should show whether the simulation itself is stable.

Track:
- number of independent replications,
- running mean/effect estimate as replications accumulate,
- Monte Carlo standard error,
- CI stability,
- run failure rate,
- retry rate,
- provider/model distribution,
- seed balance.

Add a "replication sufficiency" plot:
- x-axis = number of runs,
- y-axis = estimated effect / CI width.

This is more informative than conventional power language alone for stochastic simulations.

---

# 49. Experiment Design and Power / Precision Planning

Before launch, the Experiment Builder should support planning.

Inputs:
- expected effect size or minimum meaningful effect,
- number of conditions,
- paired vs independent design,
- desired precision / CI width,
- alpha/power where conventional formulas apply,
- anticipated run failure rate,
- cost per run.

Outputs:
- recommended number of independent runs,
- total runs,
- total episodes,
- estimated API cost,
- estimated runtime.

For complex longitudinal or agentic designs, support **simulation-based power/precision analysis** rather than forcing closed-form formulas.

---

# 50. Results Table Generator

Generate publication-ready tables directly from saved Analysis Plans.

Minimum outputs:

## Descriptive table
- condition,
- N independent runs,
- episodes,
- mean,
- SD,
- median,
- IQR.

## Main test table
- estimand,
- contrast,
- effect,
- SE,
- 95% CI,
- test/model,
- p,
- adjusted p/q,
- effect size.

## Robustness table
- specification,
- effect,
- CI,
- p/q,
- N.

## Adaptation table
- immediate shock loss,
- recovery time,
- deficit area,
- repertoire change.

Export:
- CSV,
- XLSX,
- LaTeX,
- HTML,
- DOCX-ready table.

---

# 51. Figure Builder

Allow researchers to save a visualization as a versioned `EORL Figure Specification`.

Fields:
- experiment,
- data/filter specification,
- metric version,
- visualization type,
- grouping,
- uncertainty method,
- labels,
- annotation,
- generated timestamp.

Export:
- SVG,
- PNG,
- PDF,
- underlying CSV.

Every exported figure should include a sidecar JSON manifest so it can be regenerated.

---

# 52. Statistical Result Provenance

Create `EORL Analysis Result`.

Each result must point to:
- Analysis Plan,
- Experiment,
- Run IDs,
- Branch IDs if applicable,
- Metric Definition version,
- event filters,
- code version,
- statistical package/version,
- result timestamp.

Store:
- model formula,
- coefficient table,
- diagnostics,
- effect sizes,
- CI,
- raw and adjusted p-values.

A user should be able to click any reported result and see exactly which runs generated it.

---

# 53. Front-End Screens to Add

Add these to the existing UI roadmap:

```text
Scientific Cockpit
Process Explorer
Path Repertoire Explorer
Adaptation / Event-Study View
Network Explorer
Mechanism / Ablation Dashboard
Analysis Plan Builder
Statistical Results
Robustness Workbench
Replication Diagnostics
Power / Precision Planner
Results Table Generator
Figure Builder
```

---

# 54. Visualization Acceptance Tests

## 54.1 Cross-filter test
Selecting a condition/path in one panel must update linked panels consistently.

## 54.2 Provenance test
Every figure/result must expose contributing Run IDs and metric version.

## 54.3 Independence warning test
If user attempts a between-condition t-test using episodes as independent rows, block the analysis or require explicit hierarchical specification.

## 54.4 Paired-branch test
Shared-history branches must be recognized as paired by default.

## 54.5 Reproducible figure test
Saved figure specification + manifest must regenerate the same underlying data and layout.

## 54.6 Export test
Every visualization must permit export of both image and underlying data.

---

# 55. Priority Update for November Prototype

Add to **P0** if feasible:
- Scientific Cockpit with core KPIs,
- Process Explorer with DFG + episode swimlane,
- adaptation trajectory,
- run-level distribution comparison,
- basic Analysis Plan object,
- independent-run guardrail,
- Welch/permutation comparison,
- effect size + CI,
- trace-linked result provenance.

Add to **P1**:
- mixed-effects longitudinal models,
- paired-branch inference,
- equivalence tests,
- event-study view,
- network explorer,
- robustness forest plot,
- replication stability,
- publication table export.

Add to **P2**:
- QAP/MRQAP,
- survival analysis UI,
- full power simulation,
- automated result narrative,
- advanced sequence clustering,
- theory-mechanism path visualization.

---

# 56. Design Principle for the Analysis Layer

The analysis layer should communicate a strong scientific norm:

> **EORL does not merely show that two simulated conditions are different. It shows how organizational structures produced different process histories, quantifies the uncertainty across independent organizational replications, identifies the mechanism through trace-linked evidence, and makes the full inference reproducible.**

That is the standard to build toward.
