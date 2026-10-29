# EORL Lab: Complete Build Specification for an AI Coding Agent

**Project:** Executable Organizational Routine Laboratory (EORL)  
**Target:** Frappe / ERPNext v14, installed on the existing ERPNext site  
**Current legacy app:** `erp_research`  
**New app to build:** `eorl_lab`  
**Primary scientific use case:** agentic routinization and the adaptive-repertoire paradox  
**Design principle:** build a reusable research instrument, not a one-off demo

---

## 0. Your mission

Build a new Frappe application called **`eorl_lab`** that turns the existing ERPNext instance into a configurable, auditable, reproducible laboratory for experiments in which multiple autonomous AI agents repeatedly enact organizational routines against persistent ERP state.

The existing `erp_research` app was built for a prior human-AI experiment. It already demonstrates that the ERP instance can expose semantic tools, execute agentic actions, persist chat/tool traces, and log behavioral events. **Do not extend that app into the new laboratory. Do not break it.** Treat it as a source of working implementation patterns and ERP semantics only.

The new app must support two scientific contributions simultaneously:

1. **Reusable research infrastructure.** Other organizational and social-science researchers should be able to define agents, organizational architectures, memory systems, scenarios, shocks, experimental factors, and repeated runs from a front end, then export a complete reproducibility bundle.
2. **AI-enabled theory building.** The infrastructure must make competing organizational mechanisms executable and empirically discriminable. The first theory program studies whether agentic autonomy changes the relationship among routine coherence, endogenous process variety, adaptive repertoire, and post-shock adaptation.

The laboratory is **not** a synthetic human-subject system and it is **not** a claim to reproduce a whole organization. It is a controlled computational representation of a **bounded recurrent organizational routine** populated by autonomous computational actors.

---

# 1. Architectural decision: create a separate Frappe app

Create a separate app named `eorl_lab` and install it on the same site as ERPNext and `erp_research`.

### Why a separate app is mandatory

The legacy `erp_research` code is structurally tied to the prior human experiment. It contains:

- Prolific participant provisioning and human research sessions;
- a site-wide `ai_mode` switch;
- a Claude-specific conversational loop;
- human confirmation and rejection of write actions;
- a purchasing-specific scope guardrail;
- chat-widget behavior;
- human navigation events;
- a tool surface designed for a single assistant-user dyad.

EORL requires a different unit of execution: **experiment -> run -> episode -> actor -> decision/action/event**. It requires multiple persistent agents, agent-to-agent communication, configurable memories, organizational authority, repeated episodes, environmental shocks, run snapshots, controlled replications, counterfactual replay, and theory-specific process metrics.

Keeping EORL separate provides:

- clean public release of the research artifact;
- no regression risk to the completed human experiment;
- clear data provenance;
- independent database migrations;
- independent roles and permissions;
- a modular scientific API;
- future installation on any compatible ERPNext site without requiring the human-study app.

### Dependency policy

`eorl_lab` may depend on ERPNext/Frappe. It should **not require `erp_research` as a dependency**.

Where the legacy app contains useful ERP primitives, either:

- reimplement them cleanly in the new adapter layer; or
- temporarily call stable whitelisted endpoints through an explicit legacy adapter, with a TODO to remove the dependency before public release.

The preferred final state is no dependency on `erp_research`.

---

# 2. Scientific object and first experiment

## 2.1 Unit of representation

EORL represents an **organizational routine**, not an entire organization.

A routine is represented through:

- differentiated organizational roles;
- actor-specific information access;
- authority and action rights;
- recurrent interdependent work;
- ERP artifacts and persistent state;
- communication relationships;
- local and shared memory;
- environmental conditions;
- repeated performances;
- observable consequences.

The first implementation uses a recurrent **procure-to-pay** routine because the current ERPNext instance and prior agent layer already support the buying cycle.

## 2.2 First theoretical phenomenon

The first theory program is **agentic routinization and the adaptive-repertoire paradox**.

We do not assume that greater agentic autonomy standardizes routines. Competing theoretical possibilities must remain open:

- broader autonomy may increase actor continuity and path coherence, creating dominant and efficient routine pathways;
- broader autonomy may instead expand process variety because agents can discover, remember, and recombine exception-handling paths;
- any coherence gained under stable conditions may improve routine efficiency while reducing the diversity of viable pathways available after an environmental regime shift;
- alternatively, autonomy may preserve or expand the adaptive repertoire and improve adaptation.

The infrastructure must therefore let the researcher distinguish among these possibilities rather than encode one result into agent prompts.

## 2.3 Primary experimental contrast

The first prototype must support at least two organizational architectures that use the **same scenario stream**:

### Architecture A: Specialist / handoff architecture

- Purchasing Agent
- Purchasing Manager Agent
- Warehouse Agent
- Accounts Payable Agent
- narrow role-specific action rights;
- explicit handoffs across process stages;
- limited cross-stage autonomy.

### Architecture B: Broader-autonomy architecture

- same underlying routine and environmental events;
- one or more agents can act across multiple process stages;
- fewer mandatory handoffs;
- greater actor continuity;
- same external ground truth and objective task requirements.

Later architectures should be configurable without code changes, including central coordination, decentralized peer networks, shared-memory organizations, and hierarchical approval structures.

## 2.4 Stable and shock phases

Each run contains repeated episodes. A recommended default is:

- episodes 1-20: warm-up / baseline;
- episodes 21-100: stable-environment routine formation;
- episodes 101-140: post-shock adaptation;
- optional episodes 141-200: recovery / second regime.

The shock must change the **environmental distribution**, not arbitrarily damage an agent. Examples include:

- previously reliable suppliers becoming unreliable;
- a price/reliability tradeoff reversing;
- quality failures becoming concentrated in a supplier class;
- new combinations of invoice and receipt exceptions;
- lead times becoming more volatile;
- the frequency of rare exceptions increasing.

Every shock must be deterministic given the run seed and encoded in the run manifest.

---

# 3. Current legacy capability to preserve conceptually

The legacy `erp_research` app already demonstrates several capabilities that EORL should preserve in generalized form:

1. **ERP context and semantic knowledge** about ERPNext modules, DocTypes, document lifecycles, and buying workflows.
2. **Read tools** equivalent to record search and report execution.
3. **Write tools** equivalent to document creation and update.
4. **Agentic execution** of PO, Purchase Receipt, Purchase Invoice, and Payment Entry.
5. **Persistent messages and tool results.**
6. **Behavioral event logging.**
7. **Retry and provider-call handling.**

However, EORL must replace the single-assistant/human-session abstractions with experiment/run/episode/actor abstractions.

### Important legacy code that must NOT be copied blindly

Do not reproduce these legacy assumptions in the new lab:

- global `ai_mode` in site configuration;
- model name hard-coded in request functions;
- Anthropic-only provider logic;
- Prolific/user-session semantics;
- browser navigation as a core agent action;
- user confirmation dialogs;
- general `create_document` permissions without an explicit EORL authority check;
- silent `ignore_permissions=True` as the primary authorization mechanism;
- monkey-patching ERP validation logic;
- one shared conversation history as the agent's memory model;
- one purchasing-specific system prompt for every actor.

All consequential EORL actions must pass through a laboratory authority layer and remain valid ERPNext transactions.

---

# 4. High-level system architecture

```text
+------------------------------------------------------------------+
|                        EORL RESEARCH UI                           |
| Experiment Studio | Agent Studio | Architecture | Scenarios      |
| Run Monitor | Trace Explorer | Compare Runs | Export/Reproduce   |
+----------------------------+-------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                       EORL APPLICATION LAYER                      |
| Experiment Service | Run Service | Scenario Service              |
| Actor Runtime | Memory Service | Communication Service           |
| Authority Firewall | Metric Service | Export/Reproduction        |
+----------------------------+-------------------------------------+
                             |
          +------------------+-------------------+
          |                                      |
          v                                      v
+-----------------------------+      +-----------------------------+
|      MODEL PROVIDERS        |      |       EVENT / TRACE STORE   |
| OpenAI-compatible           |      | Run manifest                |
| Anthropic                   |      | Observation events          |
| local/open-weight           |      | Memory events               |
| deterministic/rule baseline |      | Messages / decisions        |
+-----------------------------+      | Tool calls / authorization  |
                                     | ERP before/after mutations  |
                                     | Outcomes / metrics           |
                                     +-------------+---------------+
                                                   |
                                                   v
                                     +-----------------------------+
                                     |       ERP ADAPTER           |
                                     | semantic read tools         |
                                     | semantic action tools       |
                                     | ERP state snapshots         |
                                     +-------------+---------------+
                                                   |
                                                   v
                                     +-----------------------------+
                                     |         ERPNext v14         |
                                     | authoritative org state     |
                                     +-----------------------------+
```

The **ERP state is authoritative**. Agent narrative claims never substitute for actual ERP state.

---

# 5. Frappe app structure

Create approximately the following structure. Adjust names to Frappe conventions, but preserve separation of concerns.

```text
apps/eorl_lab/
  eorl_lab/
    hooks.py
    modules.txt
    patches.txt
    eorl_lab/
      doctype/
        eorl_settings/
        eorl_model_profile/
        eorl_memory_profile/
        eorl_tool_policy/
        eorl_agent_template/
        eorl_architecture/
        eorl_scenario/
        eorl_regime_shift/
        eorl_experiment/
        eorl_run/
        eorl_episode/
        eorl_event/
        eorl_metric/
      page/
        eorl_lab/
        eorl_experiment_studio/
        eorl_agent_studio/
        eorl_architecture_designer/
        eorl_scenario_studio/
        eorl_run_monitor/
        eorl_trace_explorer/
        eorl_compare_runs/
        eorl_reproducibility/
      api/
        experiments.py
        runs.py
        agents.py
        traces.py
        metrics.py
        exports.py
      runtime/
        orchestrator.py
        actor.py
        decision.py
        communication.py
        authority.py
        stopping.py
      providers/
        base.py
        openai_compatible.py
        anthropic.py
        deterministic.py
      memory/
        base.py
        recent.py
        episodic.py
        shared.py
        vector.py
      erp/
        adapter.py
        registry.py
        buying.py
        accounting.py
        stock.py
        snapshots.py
      scenarios/
        generator.py
        procurement.py
        shocks.py
        ground_truth.py
      observability/
        events.py
        context.py
        exporter.py
        replay.py
      analysis/
        paths.py
        sequence.py
        coherence.py
        repertoire.py
        recovery.py
        networks.py
      fixtures/
      tests/
  pyproject.toml
  README.md
```

---

# 6. Configuration model: everything should be configurable from the UI

Use ordinary Frappe DocTypes for configuration and a custom front end for composing them into experiments. Researchers should not need to edit Python to change an experimental condition.

## 6.1 `EORL Settings` (Single DocType)

Fields:

- enabled
- default_lab_company
- default_timezone
- default_provider_profile
- default_max_episode_steps
- default_wallclock_timeout_seconds
- default_event_storage_mode
- artifact_export_root
- allow_proprietary_models
- enable_cost_tracking
- enable_prompt_snapshotting
- enable_erp_diff_capture
- enable_memory_snapshotting
- canonical_seed
- local_run_worker_queue
- max_parallel_local_runs
- external_worker_callback_secret_reference

Secrets must not be stored as ordinary plaintext DocType fields. Store only a configuration key/reference; load secrets from site config or environment variables.

## 6.2 `EORL Model Profile`

A reusable model configuration.

Fields:

- profile_name
- provider: `openai_compatible | anthropic | deterministic`
- base_url
- api_key_reference
- model_name
- temperature
- top_p
- max_tokens
- timeout_seconds
- max_retries
- seed_if_supported
- tool_call_mode
- structured_output_mode
- reasoning_mode_if_supported
- request_headers_json
- enabled

Every run must snapshot the resolved profile and record the actual model identifier returned by the provider if available.

## 6.3 `EORL Memory Profile`

Fields:

- profile_name
- local_memory_enabled
- local_backend: `recent | episodic | vector | none`
- local_retention_episodes
- local_top_k
- recency_weight
- similarity_weight
- outcome_weight
- summarization_enabled
- summary_interval
- forgetting_enabled
- forgetting_half_life
- shared_memory_enabled
- shared_backend
- shared_visibility_scope
- shared_write_policy: `all | successes_only | curated | none`
- shared_top_k
- embedding_model_profile

Every memory retrieval and write must be logged with the exact retrieved/written record IDs.

## 6.4 `EORL Tool Policy`

A named permission bundle independent of the prompt.

Fields:

- policy_name
- allowed_semantic_tools (child table)
- allowed_read_scopes
- allowed_write_scopes
- allowed_docstatus_transitions
- may_submit_documents
- may_cancel_documents
- may_approve
- may_request_approval
- may_message_agents
- allowed_message_targets
- max_tool_calls_per_step
- max_write_actions_per_episode
- escalation_policy

Prompts may describe authority, but **the authority service must enforce it outside the model**.

## 6.5 `EORL Agent Template`

This is a theory-bearing organizational actor specification, not a human personality profile.

Fields:

- template_name
- organizational_role
- role_description
- responsibilities
- local_goal
- global_goal_context
- information_scope
- authority_description
- model_profile
- memory_profile
- tool_policy
- initial_system_instructions
- decision_schema_version
- communication_enabled
- max_messages_per_episode
- max_decisions_per_episode
- enabled

Optional theory variables, only when explicitly part of a study:

- local_goal_weight
- global_goal_weight
- compliance_weight
- search_budget
- communication_budget

Do not add psychological constructs such as trust, emotion, identity, or personality unless a future study provides a defensible operationalization.

## 6.6 `EORL Architecture`

Defines the organizational arrangement.

Fields:

- architecture_name
- description
- actor slots (child table: slot_id, agent_template, count)
- supervision edges
- communication edges
- workflow handoff rules
- decision-right assignments
- shared-memory assignment
- coordination mode
- central_coordinator_slot
- allowed_cross_stage_actions
- escalation graph
- approval graph

The architecture must be exportable to deterministic JSON/YAML.

## 6.7 `EORL Scenario`

Fields:

- scenario_name
- routine_type
- generator_class
- base_seed
- episode_count
- warmup_episode_count
- supplier_count
- item_count
- demand_distribution_json
- lead_time_distribution_json
- quality_distribution_json
- price_distribution_json
- exception_family_config_json
- compound_exception_probability
- ground_truth_policy_version
- reset_strategy
- dataset_fixture_version

## 6.8 `EORL Regime Shift`

Fields:

- shift_name
- trigger_episode
- shift_type: `abrupt | gradual`
- parameter_delta_json
- description
- expected_observable_change
- hidden_from_agents

A regime shift changes environmental ground truth. It must never directly change the agent prompt to tell the agent that the world changed unless the experiment explicitly manipulates that information.

## 6.9 `EORL Experiment`

Fields:

- experiment_name
- research_question
- theoretical_mechanism
- primary_outcomes
- architecture levels
- scenario
- regime shift
- factor table
- repetitions_per_cell
- seed strategy
- model replication strategy
- stopping rules
- pre_registered_hypotheses_or_competing_predictions
- status
- notes

Support full factorial and explicit cell definitions.

## 6.10 `EORL Run`

Each run is immutable after launch except for operational status fields.

Fields:

- run_id
- experiment
- cell_id
- repetition
- run_seed
- status: `queued | initializing | running | completed | failed | aborted`
- started_at
- ended_at
- current_episode
- architecture_snapshot_json
- agent_snapshots_json
- scenario_snapshot_json
- regime_shift_snapshot_json
- provider_snapshots_json
- code_commit
- app_version
- ERPNext_version
- Frappe_version
- site_fingerprint
- run_manifest_hash
- failure_reason
- event_count
- total_tokens
- total_cost

## 6.11 `EORL Episode`

Fields:

- run
- episode_number
- scenario_case_id
- environmental_state_hash
- phase: `warmup | stable | shock | recovery`
- started_at
- ended_at
- status
- ground_truth_json
- outcome_json
- process_signature
- success
- cycle_steps
- cycle_time_simulated
- cycle_time_wallclock

## 6.12 `EORL Event`

Use **one append-only high-volume event type** rather than proliferating a separate DocType for each event family.

Indexed fields:

- event_id
- run
- episode
- sequence_no
- wallclock_timestamp
- simulated_timestamp
- event_type
- actor_slot
- actor_instance_id
- trace_id
- span_id
- parent_span_id
- correlation_id
- target_type
- target_id
- success
- payload_json
- payload_hash

Event types must include at minimum:

- `run_initialized`
- `episode_initialized`
- `environment_observed`
- `agent_context_built`
- `memory_query`
- `memory_retrieval`
- `agent_message_sent`
- `agent_message_received`
- `model_request`
- `model_response`
- `decision_parsed`
- `tool_requested`
- `tool_authorized`
- `tool_denied`
- `tool_result`
- `erp_state_before`
- `erp_mutation`
- `erp_state_after`
- `memory_write`
- `episode_outcome`
- `metric_computed`
- `error`
- `run_completed`

Do not store hidden chain-of-thought. Store the explicit structured decision, any model-visible explanation field requested by the study, and the complete observable input/output/tool trace required to reconstruct behavior.

## 6.13 `EORL Metric`

Fields:

- run
- episode optional
- phase optional
- metric_name
- metric_value
- metric_json
- metric_version
- computed_at

---

# 7. Front-end requirements

The front end is a core research component, not decoration. A researcher should be able to design and run an experiment without editing Python or JSON manually.

Use standard Frappe DocType forms where they are appropriate, plus purpose-built Desk pages for experiment composition, monitoring, and trace exploration.

## 7.1 EORL Lab home

Route suggestion: `/app/eorl-lab`

Display:

- active experiments;
- queued/running runs;
- recent completed runs;
- failed runs;
- aggregate token/cost usage;
- latest code version;
- provider health;
- ERP lab-state health;
- quick links to Agent Studio, Experiment Studio, Run Monitor, Trace Explorer, Compare Runs, and Export.

## 7.2 Agent Studio

Route: `/app/eorl-agent-studio`

Functions:

- create/edit/clone agent templates;
- assign model profile;
- assign memory profile;
- assign tool policy;
- inspect effective system prompt;
- inspect effective tool list;
- validate that prompt authority matches enforced authority;
- test one isolated decision using a dry-run fixture;
- show configuration diff between templates.

## 7.3 Architecture Designer

Route: `/app/eorl-architecture-designer`

Provide a graphical or structured node-edge editor.

The page must support:

- drag/add actor slots;
- supervision edges;
- allowed communication edges;
- handoff rules;
- approval edges;
- memory-sharing groups;
- cross-stage authority;
- central coordinator designation;
- architecture validation.

The resulting architecture must serialize to deterministic JSON.

A simple SVG or lightweight network component is sufficient. Do not make a heavyweight front-end framework a dependency unless necessary.

## 7.4 Scenario Studio

Route: `/app/eorl-scenario-studio`

Configure:

- routine type;
- supplier/item populations;
- demand and lead-time distributions;
- exception families;
- exception probabilities;
- ground-truth relationships;
- regime shift;
- number of episodes;
- seed.

Provide a **Preview Scenario Stream** button that generates the first N cases without running agents, so the researcher can inspect the environmental distribution and verify the shock.

## 7.5 Experiment Studio

Route: `/app/eorl-experiment-studio`

Implement a wizard with these steps:

1. Research question and theoretical mechanism.
2. Scenario and shock.
3. Architecture levels.
4. Agent/model assignments.
5. Memory configuration.
6. Experimental factors and levels.
7. Repetitions and seeds.
8. Metrics.
9. Reproducibility settings.
10. Review / launch.

Before launch, show the implied cell count and total run count.

Example:

```text
2 architectures x 3 model families x 25 repetitions = 150 runs
```

Allow `Validate only`, `Launch pilot`, and `Launch full experiment`.

## 7.6 Run Monitor

Route: `/app/eorl-run-monitor`

Show:

- run status;
- current episode;
- current actor;
- latest event;
- ERP documents created;
- token usage;
- cost;
- error count;
- elapsed wall time;
- phase marker (stable / shock / recovery);
- live event stream.

Controls:

- pause after current step;
- abort;
- retry failed episode;
- clone run;
- download manifest;
- open trace explorer.

## 7.7 Trace Explorer

Route: `/app/eorl-trace-explorer`

This page is essential for auditability.

Researcher must be able to select:

`experiment -> run -> episode -> actor / trace`

and see a chronological reconstruction:

1. environmental state;
2. actor-visible state;
3. retrieved memory;
4. messages received;
5. model request metadata;
6. structured model decision;
7. tool requested;
8. authority decision;
9. ERP state before;
10. tool result;
11. ERP state after;
12. messages sent;
13. memory written;
14. episode outcome.

Include filters for event type, actor, ERP document, error, tool, and correlation ID.

Provide a **Replay from here** action that creates a new counterfactual run branch. Never overwrite the original run.

## 7.8 Compare Runs

Route: `/app/eorl-compare-runs`

Allow comparison by:

- experiment cell;
- architecture;
- model profile;
- seed pair;
- pre/post-shock phase.

Core visualizations:

- objective performance;
- cycle steps;
- path frequency distribution;
- sequence entropy;
- actor switch rate;
- actor-continuity/coherence;
- number of unique paths;
- number of viable paths;
- new-path generation after shock;
- recovery trajectory;
- error correlation;
- communication network;
- tool-use distribution;
- memory retrieval distribution.

Use Frappe Charts where adequate. Use a lightweight external visualization library only when network or sequence visualization genuinely requires it.

## 7.9 Reproducibility / Export

Route: `/app/eorl-reproducibility`

One-click export of:

```text
experiment.yaml
run_manifest.json
resolved_agent_configs/
resolved_prompts/
scenario_stream.jsonl
events.jsonl
metrics.csv
process_paths.csv
architecture.json
model_metadata.json
environment_metadata.json
requirements-lock.txt or equivalent
code_commit.txt
README_REPRODUCE.md
```

Add optional Parquet exports for high-volume events.

The export must be enough for another researcher to recompute all reported metrics from raw events without access to the model provider.

---

# 8. Agent runtime

## 8.1 Provider abstraction

Create a common interface such as:

```python
class ModelProvider(ABC):
    def generate(self, request: ModelRequest) -> ModelResponse:
        ...
```

Implement at minimum:

- `OpenAICompatibleProvider`
- `AnthropicProvider`
- `DeterministicProvider`

Do not hard-code a particular model in the run loop.

`OpenAICompatibleProvider` should work with local servers such as vLLM or other OpenAI-compatible inference endpoints.

## 8.2 Structured decisions

Every actor response must parse into a versioned schema. Example:

```json
{
  "decision_version": "1.0",
  "state_assessment": "brief observable summary",
  "intended_action": "tool_name_or_message",
  "tool_arguments": {},
  "recipient": null,
  "confidence": 0.72,
  "decision_basis": "brief explicit explanation, not hidden chain-of-thought",
  "stop": false
}
```

If parsing fails:

1. log failure;
2. retry with structured repair instruction;
3. after max attempts, mark actor step failed and follow configured escalation policy.

## 8.3 Actor context

A model request should be assembled from explicit channels:

```text
ROLE / RESPONSIBILITIES
ORGANIZATIONAL GOALS
AUTHORITY SUMMARY
CURRENT EPISODE OBJECTIVE
ACTOR-VISIBLE ERP STATE
MESSAGES RECEIVED
RETRIEVED LOCAL MEMORY
RETRIEVED SHARED MEMORY
AVAILABLE TOOLS
OUTPUT SCHEMA
```

Do not expose global ground truth unless the actor is allowed to know it.

## 8.4 Agent persistence

An actor instance persists across episodes within a run. Its configuration is immutable for that run, while its memory may evolve according to its memory profile.

At run initialization:

- instantiate stable actor IDs;
- resolve templates;
- snapshot prompts;
- snapshot model profiles;
- snapshot tool policies;
- initialize memory namespaces.

At episode boundaries, retain or reset state according to the experiment configuration.

---

# 9. Authority firewall

This is one of the most important components.

Every consequential tool request must be evaluated by a deterministic authority service **outside the model**.

Example API:

```python
Decision = authority.evaluate(
    run_id=run_id,
    actor_id=actor_id,
    tool_name=tool_name,
    tool_args=tool_args,
    current_erp_state=state,
)
```

Return:

```json
{
  "allowed": true,
  "reason_code": "POLICY_ALLOW",
  "policy_version": "...",
  "resolved_scope": {...}
}
```

Log all allow and deny decisions.

The model must never be able to elevate its own permissions by claiming a role in text.

Do not use `ignore_permissions=True` as the conceptual authority mechanism. If server-side ERP operations require elevated execution, the EORL policy check must occur first and must be logged. Wherever feasible, also use ERPNext roles/permissions as defense in depth.

Do not monkey-patch ERPNext validators. A transaction that violates ERP rules should fail and the failure should become part of the observable organizational process.

---

# 10. Semantic ERP tool registry

The legacy code exposes generic `search_records`, `get_report`, `create_document`, and `update_document`. Retain generic primitives internally if useful, but **agents should primarily receive narrow semantic tools** because these map more cleanly to organizational functions and authority.

Initial procurement tools should include:

### Read / sensing

- `get_pending_material_requests`
- `get_material_request`
- `get_item_requirements`
- `get_inventory_position`
- `get_supplier_options`
- `get_supplier_history`
- `get_open_purchase_orders`
- `get_purchase_order`
- `get_receipt_status`
- `get_invoice_status`
- `get_payment_status`
- `get_exception_context`

### Communication / coordination

- `message_agent`
- `request_information`
- `request_approval`
- `escalate_exception`

### Consequential actions

- `create_purchase_order`
- `submit_purchase_order`
- `create_purchase_receipt`
- `submit_purchase_receipt`
- `create_purchase_invoice`
- `submit_purchase_invoice`
- `create_payment_entry`
- `submit_payment_entry`
- `update_permitted_document`

Each tool must have:

- typed arguments;
- typed return object;
- authority requirements;
- preconditions;
- postconditions;
- event hooks;
- ERP before/after state capture for affected documents.

The tool result must reflect actual ERP state after execution.

---

# 11. Scenario generator and environmental ground truth

This is what separates a scientific simulation from free-form agent roleplay.

Build a deterministic procurement scenario generator in which environmental states exist independently of what the agents believe.

Each episode should create a case object similar to:

```json
{
  "case_id": "CASE-000123",
  "episode": 123,
  "demand": {"MILK-001": 600, "CREAM-001": 250},
  "candidate_suppliers": ["SUP-A", "SUP-B", "SUP-C"],
  "latent_ground_truth": {
    "SUP-A": {"delivery_probability": 0.95, "quality_probability": 0.89, "price": 1.32},
    "SUP-B": {"delivery_probability": 0.78, "quality_probability": 0.98, "price": 1.20}
  },
  "exception": {
    "family": "delivery_risk",
    "severity": 0.7
  }
}
```

Ground truth should drive realized outcomes probabilistically and must be stored separately from actor-visible information.

Initial exception families:

- supplier delivery risk;
- quality failure;
- price anomaly;
- quantity mismatch;
- receipt discrepancy;
- invoice mismatch;
- approval constraint;
- payment constraint;
- compound exception.

The scenario generator must be seed deterministic.

---

# 12. State isolation and reset strategy

This is a critical technical issue. Experimental runs must not contaminate one another through shared ERP state.

## Prototype strategy

For the November 1 prototype, prioritize **sequential isolated runs** with deterministic state reset.

Implement one of these strategies, in preference order:

1. restore a known lab-company database snapshot/fixture before each run; or
2. delete/recreate all EORL-generated transactional documents and restore controlled master-state fixtures; or
3. use run-prefixed master/transaction data with strict filtering if full reset is impractical.

Every generated document must carry a run identifier through a custom EORL field or deterministic naming/tagging mechanism where possible.

## Scalable strategy

For parallel ACCESS/HPC experiments, design toward **ephemeral ERPNext site clones or isolated containerized lab instances per worker/batch**. Do not run multiple mutating experimental conditions concurrently against one shared ERP company unless isolation has been demonstrated.

The run manifest must record the reset/isolation strategy.

---

# 13. Orchestrator and episode lifecycle

Implement the orchestrator as an explicit state machine or discrete-event loop, not as uncontrolled agents chatting indefinitely.

Recommended episode lifecycle:

```text
1. initialize case / environment
2. write exogenous state into ERP as appropriate
3. determine enabled actor(s)
4. build actor-visible state
5. retrieve local/shared memory
6. deliver pending messages
7. request structured decision
8. parse decision
9. if message -> deliver/log
10. if tool -> authority check
11. execute tool if allowed
12. record ERP before/after state
13. update enabled actors / workflow state
14. write memory according to policy
15. evaluate completion / failure / timeout
16. compute episode outcome
17. emit process path
18. advance to next episode
```

The orchestrator must have explicit limits:

- max steps per episode;
- max tool calls;
- max inter-agent messages;
- max retries;
- max wall-clock time;
- deadlock detection;
- loop detection;
- failure state.

No run should be able to hang indefinitely.

---

# 14. Memory system

Memory is an experimental manipulation, not hidden convenience state.

Implement a common interface:

```python
class MemoryStore(ABC):
    def retrieve(self, query, actor_context, k): ...
    def write(self, record): ...
    def snapshot(self): ...
    def reset(self): ...
```

Support at minimum:

1. **No memory**
2. **Recent-k memory**
3. **Local episodic memory**
4. **Shared organizational memory**
5. **Vector retrieval memory** as optional extension

Memory record schema:

```json
{
  "memory_id": "...",
  "run_id": "...",
  "actor_id": "...",
  "episode": 37,
  "domain": "supplier_delivery",
  "case_summary": "...",
  "action": "...",
  "outcome": "...",
  "success": true,
  "salience": 0.81,
  "created_at": "..."
}
```

Every retrieval result must be logged so a researcher can reconstruct exactly what prior information was available to the agent.

---

# 15. Inter-agent communication

Messaging must be explicit and observable.

`message_agent` should create an immutable message event with:

- sender;
- recipient;
- episode;
- message type;
- message content;
- correlation ID;
- delivered timestamp;
- read timestamp;
- optional linked task/document.

Communication topology must be enforced by the architecture, not just described in prompts.

Support future experimental manipulations such as:

- full network;
- functional silos;
- hierarchy-only;
- central broker;
- sparse peer network;
- message budgets;
- delayed communication.

---

# 16. Observability and auditability

Observability is a scientific requirement.

## 16.1 Context propagation

Create a runtime context carrying:

```python
ExperimentContext(
    experiment_id,
    run_id,
    cell_id,
    episode_id,
    actor_id,
    trace_id,
    span_id,
    parent_span_id,
    correlation_id,
    sequence_no,
)
```

Every event must inherit this context.

## 16.2 ERP diffs

For every consequential ERP tool call, capture:

- affected document identifiers;
- relevant fields before;
- relevant fields after;
- docstatus transition;
- success/failure;
- Frappe exception if failed.

Avoid dumping the entire database on every action. Capture targeted semantic diffs plus periodic state hashes/snapshots.

## 16.3 Model observability

Record:

- provider;
- resolved model ID;
- request timestamp;
- input prompt hash;
- optionally complete prompt snapshot according to setting;
- tool schema version;
- model parameters;
- output text/structured decision;
- token counts;
- latency;
- retry count;
- provider request ID where available;
- cost estimate.

## 16.4 Event immutability

After a run completes, its raw event history should be read-only through normal UI permissions.

Corrections should be represented as new derived-analysis versions, not edits to raw events.

## 16.5 Scalable event export

The Frappe `EORL Event` table is acceptable for the prototype. Also build an exporter that produces JSONL and Parquet for large-scale analysis so the scientific artifact is not locked into Frappe/MariaDB.

---

# 17. Process representation and theory metrics

The analysis layer must derive process data from raw events; it must not depend on hand-coded labels stored by the agent.

## 17.1 Canonical action event

Convert tool and communication events into a canonical process record:

```text
(run, episode, order, actor, organizational_function,
 process_stage, action_type, target, success, timestamp)
```

## 17.2 Process stages

Initial stages:

- REQUIREMENT
- SUPPLIER_SEARCH
- PURCHASE_ORDER
- RECEIPT
- INVOICE
- PAYMENT
- EXCEPTION
- APPROVAL

## 17.3 Core measures

Implement versioned metric functions for:

### Performance

- completion success;
- ground-truth decision accuracy;
- total financial cost;
- avoidable error cost;
- simulated cycle time;
- step count;
- failure count.

### Routine structure

- unique sequence count;
- sequence entropy;
- modal-path share;
- transition entropy;
- actor-switch rate;
- same-actor transition rate;
- average actor run length;
- functional-switch rate;
- path similarity / edit distance;
- directly-follows graph.

### Path coherence

Implement at least transparent proxies first:

- actor continuity;
- functional continuity;
- stage continuity;
- repeated-path probability.

Then add more formal path-coherence implementations if required by the paper.

### Adaptive repertoire

Do not operationalize repertoire merely as the raw number of different paths. Define a path as **viable** if it satisfies an explicitly versioned success criterion.

Compute:

- viable unique paths in stable phase;
- viable-path entropy;
- repertoire breadth by exception family;
- proportion of repertoire reused after shock;
- novel viable paths generated after shock;
- path extinction rate;
- concentration in top-k paths.

### Adaptation

- immediate post-shock performance drop;
- episodes to recover X% of pre-shock performance;
- area under recovery curve;
- post-shock error rate;
- rate of viable new-path discovery;
- change in sequence entropy;
- change in path concentration.

All metric functions must accept raw exported events so they can be recomputed outside Frappe.

---

# 18. Reproducibility requirements

Every run must generate an immutable `run_manifest.json` including:

```json
{
  "run_id": "...",
  "experiment_id": "...",
  "cell_id": "...",
  "seed": 12345,
  "code_commit": "...",
  "eorl_version": "...",
  "frappe_version": "...",
  "erpnext_version": "...",
  "architecture": {...},
  "agents": [...],
  "model_profiles": [...],
  "memory_profiles": [...],
  "tool_policies": [...],
  "scenario": {...},
  "regime_shift": {...},
  "metric_versions": {...},
  "started_at": "..."
}
```

The system must support **paired seeds**: competing architectures can receive exactly the same exogenous scenario stream.

The scenario stream should be generated before agent execution and hashed so its identity across cells can be verified.

---

# 19. Counterfactual replay

A major scientific affordance is the ability to replay the same organizational history under a different architecture.

Support:

1. save scenario stream;
2. save exogenous random draws;
3. restore initial ERP fixture;
4. launch a new run with a new architecture or memory design;
5. use the identical exogenous stream;
6. assign a new run ID and preserve lineage to the source run.

For branching from a specific episode, record:

- source run;
- branch episode;
- source state snapshot/hash;
- changed configuration;
- new run ID.

Never modify the source run.

---

# 20. Local and background execution

## Local Frappe execution

Use Frappe background jobs for pilot runs:

- queue name: configurable, e.g. `eorl`;
- one run can be one long job or a sequence of resumable episode jobs;
- prefer resumable episode/checkpoint design so failures do not lose the full run.

Run UI must continue to poll status even if the browser closes.

## External/HPC execution

Design an external worker package that can:

- pull an immutable run bundle;
- execute model calls and orchestration outside the web process;
- call the ERP adapter over authenticated HTTP or run against an isolated ERP instance;
- emit event bundles;
- upload results.

For ACCESS-scale experiments, the preferred long-run design is containerized workers and isolated ERP environments rather than hundreds of workers mutating one ERPNext site.

Provide a CLI such as:

```bash
eorl run --manifest run_manifest.json
eorl batch --experiment EXP-0004
eorl analyze --events events.jsonl --out metrics/
eorl reproduce --bundle bundle.zip
```

---

# 21. Security and roles

Create Frappe roles:

- `EORL Researcher`
- `EORL Administrator`
- `EORL Viewer`

Researchers can configure and run experiments. Administrators can configure providers and system settings. Viewers can inspect completed experiments but cannot mutate raw data.

Never expose API keys to the browser.

Do not allow an agent-generated tool name or DocType to bypass the semantic tool registry.

---

# 22. Prototype front-end workflow

For the first fully working prototype, a researcher should be able to perform this entire workflow through the browser:

1. Open EORL Lab.
2. Create/select a model profile.
3. Create four agent templates.
4. Define specialist architecture.
5. Clone it and define broad-autonomy architecture.
6. Define procurement scenario and regime shift.
7. Create experiment with Architecture as a two-level factor.
8. Choose 3 pilot repetitions and paired seeds.
9. Click **Launch Pilot**.
10. Watch runs progress.
11. Open one episode and inspect its full trace.
12. Compare architectures on process metrics.
13. Export a reproducibility bundle.
14. Reset and reproduce one selected run from the bundle.

If any of these steps requires editing Python, the prototype is not complete.

---

# 23. First default experiment configuration

Ship a fixture called `adaptive_repertoire_demo`.

Suggested defaults:

```yaml
experiment: adaptive_repertoire_demo
routine: procure_to_pay
episodes: 140
stable_phase_end: 100
shock_episode: 101
architectures:
  - specialist_handoff
  - broad_autonomy
repetitions_per_cell: 3
paired_seeds: true
model_profile: default_openai_compatible
memory:
  local: episodic
  shared: false
scenario:
  exception_families:
    - delivery_risk
    - quality_failure
    - invoice_mismatch
    - receipt_mismatch
    - compound_exception
shock:
  type: supplier_reliability_reversal
metrics:
  - objective_success
  - process_steps
  - unique_paths
  - sequence_entropy
  - actor_switch_rate
  - actor_continuity
  - viable_repertoire_size
  - viable_repertoire_entropy
  - post_shock_drop
  - recovery_area
```

For November 1, even a smaller demonstration (for example, 20 stable + 10 post-shock episodes) is acceptable if the complete architecture and traceability are visible.

---

# 24. Testing requirements

## Unit tests

At minimum:

- provider request/response normalization;
- decision schema validation;
- authority allow/deny logic;
- tool registry;
- deterministic scenario generation;
- shock application;
- memory retrieval/write;
- event creation;
- process-path extraction;
- core metric calculations;
- manifest hashing;
- export/import.

## Integration tests

1. create a deterministic one-episode procurement case;
2. run a deterministic provider actor;
3. create a real ERP transaction;
4. verify event sequence;
5. verify before/after ERP diff;
6. verify episode outcome;
7. export bundle;
8. recompute metric from exported events.

## Scientific regression test

A fixed deterministic run must always produce the same:

- scenario stream hash;
- event count;
- process path;
- outcome;
- metrics.

This test is critical for detecting accidental changes in the research instrument.

---

# 25. Migration / integration plan with the existing `erp_research` app

Do not delete or modify legacy behavior unless absolutely necessary.

## Phase A: inventory legacy primitives

Identify reusable logic in `erp_research.research.api`, especially:

- company/default resolution;
- purchase tool implementations;
- report execution;
- document linking requirements;
- date/currency/warehouse defaults.

Document all reused assumptions.

## Phase B: rewrite as explicit EORL adapter functions

Move equivalent functionality into `eorl_lab/erp/` with:

- typed request/response objects;
- no human session dependency;
- no global `ai_mode`;
- no model-provider dependency;
- no prompt logic;
- no browser navigation;
- no hidden authorization bypass.

## Phase C: validate parity

Using a fixture procurement case, compare legacy tool output with the new EORL semantic action output.

## Phase D: freeze the legacy app

Treat `erp_research` as read-only for the purpose of this new project.

---

# 26. Build order

Do not try to build the whole UI before proving one vertical slice.

## Milestone 1: app skeleton and config

Deliver:

- `eorl_lab` installable app;
- roles;
- settings/model/agent/tool-policy DocTypes;
- one lab workspace/page;
- migrations/tests green.

## Milestone 2: one vertical slice

A deterministic agent can:

- receive one procurement case;
- observe permitted ERP state;
- request one semantic action;
- pass authority check;
- create a real ERP document;
- produce full event trace;
- complete the episode.

Stop and demo this before adding multi-agent complexity.

## Milestone 3: multi-agent routine

Add:

- four persistent actor slots;
- explicit communication;
- handoffs;
- full PO -> receipt -> invoice -> payment routine;
- failure handling.

## Milestone 4: memory and repeated episodes

Add:

- local episodic memory;
- repeated cases;
- actor persistence;
- deterministic scenario stream.

## Milestone 5: architectures and shock

Add:

- specialist architecture;
- broad-autonomy architecture;
- architecture selection through config only;
- regime shift;
- paired seeds.

## Milestone 6: research front end

Complete Experiment Studio, Run Monitor, Trace Explorer, Compare Runs, and Export.

## Milestone 7: theory metrics

Implement path extraction, variety, coherence proxies, repertoire, and adaptation.

## Milestone 8: reproducibility artifact

One-click export and successful reproduction of one run from bundle.

## Milestone 9: scalable execution

External worker/HPC support, Parquet export, and isolated concurrent environments.

---

# 27. Definition of done for the November 1 prototype

The prototype is scientifically credible when all of the following are true:

- [ ] `eorl_lab` is a separate installable Frappe app.
- [ ] Existing `erp_research` behavior still works unchanged.
- [ ] At least four organizational actor templates are configurable.
- [ ] At least two organizational architectures are configurable without code edits.
- [ ] A deterministic scenario generator creates known procurement cases.
- [ ] A deterministic regime shift is implemented.
- [ ] Agents persist across episodes.
- [ ] Local memory is configurable and observable.
- [ ] Agent-to-agent communication is explicit and logged.
- [ ] Authority is enforced outside prompts.
- [ ] All ERP writes are real ERPNext transactions.
- [ ] Every consequential action has before/after evidence.
- [ ] A run manifest snapshots every experimental configuration.
- [ ] Competing architectures can receive identical paired scenario streams.
- [ ] The front end can create and launch an experiment.
- [ ] The front end can monitor active runs.
- [ ] The Trace Explorer can reconstruct an episode end-to-end.
- [ ] The analysis layer computes process paths and initial coherence/variety/repertoire metrics.
- [ ] A complete run can be exported as JSONL/CSV/YAML/JSON artifacts.
- [ ] One exported run can be reproduced or its metrics recomputed from raw traces.
- [ ] Unit and integration tests pass.
- [ ] Repository README explains installation and a five-minute demo.

---

# 28. Things you must not do

Do not:

- rebuild ERPNext;
- modify the legacy human experiment unless integration absolutely requires it;
- put experiment-critical parameters only in code constants;
- rely on prompts for security or authority;
- let agents freely mutate arbitrary DocTypes;
- call the artifact a full synthetic organization in UI/documentation;
- claim the agents are human substitutes;
- hide scenario ground truth inside agent prompts;
- use model self-reports as objective performance measures;
- store only final outcomes and discard process traces;
- use a proprietary model as the only runnable provider;
- make model provider configuration inseparable from actor configuration;
- let two concurrent experimental runs contaminate the same ERP state;
- overwrite completed raw events;
- require hidden chain-of-thought for analysis;
- silently repair ERP failures without logging them;
- use browser navigation as the primary agent execution mechanism.

---

# 29. Research-artifact framing to preserve in README and UI

Use language close to the following:

> EORL is a configurable laboratory for executing organizational routines with autonomous computational actors against persistent enterprise-system state. Researchers specify actors, information, authority, memory, communication, organizational architecture, and environmental conditions; EORL repeatedly enacts the resulting routine, supports controlled interventions and regime shifts, and records complete event-level traces from observation through organizational consequence.

And:

> The artifact is designed both as reusable research infrastructure and as an instrument for AI-enabled theory building. Its scientific purpose is not to simulate human psychology, but to make organizational mechanisms executable, manipulable, repeatable, and auditable so that competing theories can be compared through controlled computational interventions.

---

# 30. First theory-specific acceptance test

Before calling the research layer complete, demonstrate the following end-to-end comparison:

1. Generate a fixed 30-episode scenario stream with a shock at episode 21.
2. Run `specialist_handoff` on seed S.
3. Reset ERP state.
4. Run `broad_autonomy` on the identical scenario stream and seed S.
5. Export both event histories.
6. Show that the exogenous scenario hashes are identical.
7. Extract each episode's canonical process path.
8. Compute actor-switch rate, actor continuity, unique paths, sequence entropy, viable repertoire, and post-shock recovery.
9. Open one episode in Trace Explorer and reconstruct every observable step from environment to ERP outcome.
10. Recompute the same metrics from the exported JSONL without querying the live ERP database.

The result need not favor either architecture. The scientific success criterion is that the instrument makes the competing process dynamics **observable and discriminable**.

---

# 31. Deliverables from the coding agent

Return all of the following:

1. Complete `eorl_lab` Frappe app source.
2. Migration/install instructions.
3. All DocTypes and custom pages.
4. Provider abstraction and at least one open/OpenAI-compatible path plus Anthropic adapter.
5. Deterministic provider for tests.
6. Semantic ERP adapter and procurement tools.
7. Authority firewall.
8. Multi-agent orchestrator.
9. Memory subsystem.
10. Communication subsystem.
11. Scenario and shock generator.
12. Event-sourcing/observability layer.
13. Process-analysis layer.
14. Export/reproducibility subsystem.
15. Unit and integration tests.
16. `adaptive_repertoire_demo` fixture.
17. README with architecture diagram, installation steps, research concepts, and demo workflow.
18. A short `MIGRATION_FROM_ERP_RESEARCH.md` explaining what was reused conceptually and why the old app remains separate.
19. A `SCIENTIFIC_AUDIT.md` documenting each source of randomness, each place model output can affect the environment, and each independently enforced experimental constraint.

When implementation decisions differ from this specification, document the deviation and its scientific consequences rather than silently changing the design.
