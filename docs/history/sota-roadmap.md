# EORL SOTA Roadmap

**Status:** SOTA Milestone 5 delivered. Created 2026-10-29, updated 2026-10-30
(SOTA M5).

This tracks progress against `docs/specs/EORL_SOTA_DEVELOPER_BUILD_SPEC_V2_ANALYTICS.md`
("V2"), a substantially larger specification than the one `PROGRESS.md`
tracks (`docs/specs/EORL_LAB_AGENT_BUILD_SPEC_V1.md`, "V1"). **This file
runs parallel to `PROGRESS.md`, not in place of it** — `PROGRESS.md` stays
the historical record of what Milestones 1–8 built against V1 and is not
rewritten. This file is the gap analysis and forward plan against V2,
starting from exactly what V1's 8 milestones already delivered.

V2 is not a refinement of V1; it's a considerably larger scientific and
engineering scope: five explicit layers (environment/organization/actors/
process/science), a formal multi-type authority model, five distinct
memory types, a communication-policy graph, a task-allocation layer, a
process-grammar object, a construct registry, counterfactual branching
with shared history, mechanism ablation, and — section 37 onward — an
entire statistical-visualization workbench (design-aware inference,
effect sizes, equivalence testing, robustness panels, power planning,
publication tables, figure builder) that has no counterpart in V1 at all.

**Honest framing:** sections 37–56 alone (the analytics workbench) are
roughly as large as everything Milestones 1–8 built combined. This
document identifies what to build next; it does not claim a timeline.

---

## 1. What V1's work already satisfies, as-is

No rework needed — V2's principles 1–4 (ERP as authoritative state,
organization/actor separation, traceable claims, append-only events) are
already how `eorl_lab` behaves:

| V2 requirement | Already satisfied by |
|---|---|
| Separate `eorl_lab` app, `erp_research` untouched | M1 |
| ERPNext authoritative; agent narrative never substitutes for it | M2's `get_purchase_order` sensing pattern throughout M2–M5 |
| Persistent actor identity *within* a run | `EORL Agent Template` + M4's memory persistence |
| Provider abstraction | `ModelProvider` ABC (M2); only `DeterministicProvider` implemented |
| Four role-bounded agents, specialist vs. broad-autonomy | M3, M5 |
| Authority firewall (tool-level + submit-rights) | M2 `authority.evaluate()`, M3's `may_submit_documents` rule |
| Repeated episodes | M4 |
| One controlled regime shift | M5 (`EORL Regime Shift`, demand-quantity shock) |
| Event sourcing, append-only | M2 `EORL Event` |
| Immutable run manifest | M8 `build_run_manifest` |
| Process path extraction | M7 `eorl_lab.analysis.paths` |
| Core measures: actor continuity, handoffs, variety, concentration, coherence, recovery | M7 `coherence.py`/`sequence.py`/`repertoire.py`/`recovery.py` |
| Trace Explorer | M6 |
| Exportable raw traces | M6 (JSON), M8 (full zip bundle) |
| Reproducibility (deterministic baseline) | M8 `reproduce_run` |

## 2. What V1's work partially satisfies (extend, don't replace)

| V2 requirement | Current state | Gap |
|---|---|---|
| Semantic ERP adapter | 11 tools, flat `erp/buying.py` | V2 wants `erp/tools/{search,reports,purchase,stock,accounting}.py` — organizational, not urgent |
| Bounded-discretion process mode | Implicit in the orchestrator + authority firewall | No explicit `process_mode` field; no `prescribed`/`emergent` modes at all |
| Latent ground truth | `case["latent_ground_truth"]` exists on every scenario case (M2) | **Never read by any decision logic** — `DeterministicProvider` ignores it entirely. This is the single highest-leverage gap: V2's entire theory program (§15–16) depends on environment-driven, not hand-scripted, outcomes. |
| Communication | `_handoff()` sends logged messages at fixed points (M3) | Orchestrator-enforced, not agent-chosen; no `Communication Policy`/graph object; no `consult_peer`/`escalate`/`delegate` as real actions |
| Authority model | `allowed_semantic_tools` + `may_submit_documents` + `may_approve` flags | Not formalized into V2's 4 distinct types (execution/decision/approval/assignment); no hard-vs-soft constraint distinction — everything today is hard-reject |
| Memory | Episodic + recent + none (M4) | No semantic, procedural, shared, or transactive memory |
| Experiment Builder | `EORL Experiment` is 1-factor/2-level (M6) | No arbitrary factors/levels, no branch points, no ablation marking |
| Process mining | DFG, variants, entropy, concentration (M7) | No Levenshtein/optimal-matching distance, no medoid trajectories, no motifs |
| Networks | `communication_network()` only (M7) | No advice/delegation/approval/expertise-belief graphs, no longitudinal snapshots |
| Reproducibility | Exact re-run of the same config (M8) | No *counterfactual* branching — cloning a run's state at episode `t` into multiple diverging conditions sharing identical history to that point |

## 3. What does not exist at all

**Structural / experiment layer:**
- `EORL Process Grammar` (queryable transition graph: legal/illegal/
  mandatory/optional/terminal) — stages today are a hardcoded
  `tool_name -> STAGE` dict, not a data object
- `EORL Tool` registry with per-tool metadata (risk_level, cost, latency,
  discoverable, version) — today a tool is just a Python function plus a
  string in a child table
- `EORL Communication Policy`, `EORL Assignment Policy`, `EORL Task
  Assignment` — none exist; task allocation isn't a concept in the
  system at all
- `EORL Construct` registry linking theory to measurement
- `EORL Branch` + branch_id on events; counterfactual history cloning
- Mechanism-ablation marking (`this run is an ablation of run X, toggling
  Y`)
- Additional actor engines: Anthropic, OpenAI, local/open-weight,
  bounded-rational, random-baseline providers (only `DeterministicProvider`
  exists)
- Formal goals/objective weights per role (cost/delivery/quality etc.)
- `EORL Run Manifest`, `EORL Actor State`, `EORL Metric Definition` (a
  *registry* of versioned metric definitions, distinct from `EORL
  Metric`'s *results*), `EORL Reproducibility Bundle` as tracked
  DocTypes — today these are plain functions/snapshots, not first-class
  records

**The entire analytics workbench (V2 §37–56) — zero overlap with V1:**
- Scientific Cockpit (synchronized, cross-filtering experiment dashboard)
- Process Explorer UI (DFG with overlays, variant table, Sankey,
  swimlane timeline, sequence clustering, repertoire/path-genealogy
  explorer)
- Adaptation/event-study visualization, change-point diagnostics
- Distribution/effect visualization (violin/raincloud, forest, coefficient
  plots)
- Network Explorer UI
- Mechanism/Ablation dashboard
- `EORL Analysis Plan` (a saved, versioned statistical specification —
  the independence guardrail, paired-branch detection, test-family
  recommendation)
- An actual statistics engine: Welch/permutation tests, mixed-effects
  models, GEE, logistic/Poisson regression, survival analysis, TOST
  equivalence, FDR/Holm correction
- Robustness workbench, replication/Monte Carlo diagnostics, power/
  precision planner
- Results Table Generator (CSV/XLSX/LaTeX/DOCX), Figure Builder
  (versioned figure specs, SVG/PNG/PDF export)
- `EORL Analysis Result` provenance records

---

## 4. Proposed build order

V2 §32 and §55 give their own P0/P1/P2 priority tiers. Re-expressed as a
concrete sequence that extends V1's milestone numbering (continuing from
Milestone 8) rather than restarting:

### SOTA Milestone 1 — Close the structural gaps (V2 P0, non-analytics)
The foundational pieces everything else depends on:
1. **Ground-truth-driven outcomes** — make `latent_ground_truth` actually
   determine tool results probabilistically (currently inert). This is
   the single change most likely to finally give the M7 repertoire/
   adaptation metrics real signal to measure, instead of the documented
   vacuity.
2. **Formal authority model** — split today's flags into real
   execution/decision/approval/assignment authority, and add the
   hard-constraint-vs-soft-rule distinction (soft violations logged, not
   rejected).
3. **`EORL Process Grammar`** as a real DocType the orchestrator reads,
   replacing the hardcoded stage dict.
4. **`EORL Communication Policy`** as a real graph object; agent-chosen
   `consult_peer`/`escalate`/`delegate` actions, not just orchestrator
   handoffs.
5. **`EORL Task Assignment`** + assignment policies (even just
   `manager_assigned` and `round_robin` to start).

### SOTA Milestone 2 — Counterfactual branching (V2 P1 flagship capability)
Clone ERP state + actor memory + organizational state at episode `t`;
launch N branches sharing identical history to that point; verify
byte-identical history pre-branch (V2 §31.5's acceptance test). This
builds directly on M8's `reproduce_run` machinery but diverges instead of
exactly repeating.

### SOTA Milestone 3 — Memory expansion + additional actor engines
Semantic and procedural memory stores (shared/transactive are P2 per V2
§32.2 and can wait); a real LLM provider (Anthropic, since that's what
`erp_research` already used) alongside `DeterministicProvider`, so the
repertoire metrics can show genuine model-driven variety, not just
ground-truth-driven variety.

### SOTA Milestone 4 — Construct Registry + Experiment Builder expansion
`EORL Construct`; generalize `EORL Experiment` from 1-factor/2-level to
real factors/levels/replications/ablation-marking.

### SOTA Milestone 5 — Analytics workbench, phase 1 (V2 §55's P0 additions)
Minimum credible slice: Scientific Cockpit with core KPI cards, Process
Explorer (DFG + swimlane only, not the full suite), adaptation trajectory
plot, run-level distribution comparison, a basic `EORL Analysis Plan`
object with the **independence guardrail** (episodes ≠ independent
runs — enforced, not just documented), Welch/permutation test, effect
size + CI, and result provenance linking back to run IDs.

### SOTA Milestone 6+ — Everything else in P1/P2
Mixed-effects longitudinal models, paired-branch inference, equivalence
tests, network explorer, robustness workbench, replication diagnostics,
publication table/figure export, and the P2 frontier (transactive memory,
semantic consolidation, QAP/MRQAP, survival analysis UI, full power
simulation, Theory Compiler wizard).

---

## 5. SOTA Milestone 1 — Delivered

User confirmed this as the starting point (structural gaps before the
analytics workbench). Delivered:

- **Ground truth finally drives outcomes.** `eorl_lab.erp.stock
  .inspect_received_goods` draws a quality-inspection result from the
  scenario's own `latent_ground_truth[supplier].quality_probability`,
  seeded deterministically by `(case_hash, purchase_receipt)` so it's
  reproducible but genuinely scenario-driven, not scripted. Injected
  into tools via a new `_call_tool_with_context` helper
  (`eorl_lab.runtime.orchestrator`) that passes `_case` (and
  `_sender_slot`/`_communication_policy`) only to tools that declare
  those exact parameter names — an agent's own decision arguments can
  never forge them.
- **Formal authority model (V2 §12).** `EORL Tool Policy` gained
  `has_execution_authority`, `has_decision_authority`,
  `has_assignment_authority` as explicit grants alongside the existing
  `may_approve`/`may_submit_documents`. **Hard vs. soft constraints**
  (V2 §13) are now genuinely distinct: `authority.evaluate()` returns
  `soft_violations` on an otherwise-*allowed* decision — a large
  purchase order over `soft_rule_large_qty_threshold` is logged
  (`soft_rule_violation` event) but never blocked, proven alongside a
  test that a tool outside the policy's allow-list still hard-blocks
  regardless of any soft-rule configuration — the two checks are
  independent.
- **`EORL Process Grammar`** (+ `EORL Process Stage`/`EORL Process
  Transition` children): a real, queryable tool→stage map via
  `to_stage_map()`, which `eorl_lab.analysis.paths.process_path()` now
  accepts as an optional override — the analysis functions stay pure
  (plain dicts, no Frappe access); only the DocType resolver touches
  Frappe. A seed grammar reproduces the hardcoded default exactly
  (tested).
- **`EORL Communication Policy`** (+ `EORL Communication Edge`) and the
  first agent-*chosen* communication tool, `eorl_lab.organization
  .communication.message_agent`: checked against a real edge graph,
  used *alongside* (not instead of) the orchestrator-enforced
  structural handoffs. `EORL Architecture` gained a `communication_policy`
  Link field.
- **`EORL Task Assignment`**: every role, every episode, gets a real
  logged assignment record (`policy="fixed"`, since every architecture
  built so far has exactly one candidate per slot — multi-candidate
  pooling is future work) and a `task_assigned` event.
- **The empirically-grounded "variety is vacuous" finding from
  Milestone 7 is retired, with evidence, not just asserted away.** Ran
  30 real episodes (`RUN-00012`, seed 777): 2 genuine quality exceptions
  (episodes 19 and 29), handled end-to-end for real — `inspect_received_goods`
  → `escalate_quality_exception` (a real comment on ERPNext document
  `MAT-PRE-2026-00466`) → `message_agent` (delivered to Accounts
  Payable Agent) → `submit_purchase_receipt` regardless. Recomputing
  metrics on that run: **`unique_sequence_count: 2`, `sequence_entropy:
  0.353`, `modal_path_share: 0.933`** — the first nonzero variety
  numbers in this entire project. `modal_path_share` (28/30) matches
  the empirical 2-exception count exactly.
- Regression note: adding required tools to the Warehouse Agent's and
  broad-autonomy actor's decision trees broke every existing test
  fixture that pre-dated those tools (`TOOL_NOT_IN_POLICY` across 12
  tests) — expected, since those fixtures' tool policies were written
  before the tools existed. Fixed by adding the 3 new tools +
  `may_message_agents` to every affected fixture (6 test files), and
  relaxed one now-provably-flaky exact-count assertion (handoff count)
  to `assertGreaterEqual` since a quality exception now legitimately
  adds one more agent-chosen message on top of the structural handoffs.
  46/46 tests pass (33 existing + 13 new).
- **Deviation:** task assignment's "policy" is always `fixed` today —
  `round_robin`/multi-candidate pooling needs `EORL Architecture Actor
  Slot` to support multiple agent templates per `slot_id`, which would
  be a breaking change to `slot_map`'s shape used throughout the
  orchestrator; deferred rather than risked in this milestone.
  `has_decision_authority`/`has_assignment_authority` are recorded but
  not yet enforced at runtime (no provider branches on them yet).

---

## 6. SOTA Milestone 2 — Delivered

Counterfactual branching (V2 §17, §31.5's acceptance test): clone a run's
state at episode `t`, launch diverging conditions that share identical
history up to that point.

- **`branch_run(source_run_name, branch_episode, ...)`**
  (`eorl_lab.runtime.orchestrator`): validates the source run actually
  reached `branch_episode`, clones actor memory accumulated through that
  episode (`_clone_memory_through_branch_point` — copies `EORL Memory
  Record` rows into the new run; episodes themselves are never
  duplicated, only referenced), then creates a new `EORL Run` with
  `parent_run`/`branch_point_episode` set and continues the **same
  exogenous scenario stream** (identical `run_seed`) from
  `branch_point_episode + 1` onward — optionally under a *different*
  `EORL Architecture` or `EORL Regime Shift` (the actual counterfactual
  intervention). A new `EORL Branch` DocType records the lineage edge
  (`parent_run`, `source_episode`, `child_run`,
  `intervention_description`); a `run_branched` event is emitted on the
  child. Whitelisted via `eorl_lab.api.runs.branch_run`.
- **`get_full_branch_history(run_name)`**: walks a run's
  `parent_run`/`branch_point_episode` chain back to the root and
  reconstructs *one* continuous episode history by reading each
  ancestor's own episodes up to the point the next descendant diverged
  from it — the data itself is never copied between runs, only the
  read path changes. Whitelisted via `eorl_lab.api.runs
  .get_branch_history`.
- **`_run_episode_loop` gained `start_episode`** so a branch's episode
  numbering continues from where its parent left off instead of
  restarting at 1, matching how a human would read "episode 3 of this
  branch" as a continuation, not a new run.
- **Live-verified acceptance test (V2 §31.5):** ran a real 2-episode
  parent (`RUN-00072`, seed 555, broad_autonomy), then branched it twice
  at episode 2 — once continuing broad_autonomy (`RUN-00073`), once
  switching to specialist_handoff (`RUN-00074`). `get_full_branch_history`
  on both children returned **byte-identical episode 1–2 records**
  (same `run`, same episode `name`, same `scenario_case_id`) for both,
  then **diverged from episode 3 onward** (distinct episode names, owned
  by the respective child run) — both the shared-history and the
  divergence halves of the acceptance test hold. The two `EORL Branch`
  lineage records and the `run_branched` events were both created
  correctly. 6 new tests (`test_eorl_counterfactual_branching.py`) cover
  this plus: branching before the source run reached that episode raises
  (`frappe.ValidationError`); an unbranched run's history is just its own
  episodes; memory records are cloned byte-for-byte through the branch
  point (content-compared, not just counted); lineage fields persist on
  the child `EORL Run` document and the `EORL Branch` record. 52/52
  tests pass (46 existing + 6 new).
- **Pre-existing bug found and fixed in the process, unrelated to
  branching but blocking every run on this shared dev site once
  triggered:** `DeterministicProvider` never passed an explicit `rate`
  to `create_purchase_order`, relying entirely on ERPNext's own Item
  Price → `last_purchase_rate` fallback chain. That chain is
  self-referential — `last_purchase_rate` is itself set *from* each
  submitted transaction's own rate — so once any single transaction
  resolved to a rate of 0 (which happened during this milestone's own
  testing), every subsequent run on the site silently inherited rate 0
  forever, failing downstream at Payment Entry ("Paid Amount is
  mandatory"). Fixed by having both `_decide_purchasing_agent` and
  `_decide_general_purchasing_agent` pass the chosen supplier's actual
  `latent_ground_truth[supplier]["price"]` as an explicit `rate` (new
  `_supplier_rate` helper in `providers/deterministic.py`), breaking the
  circular dependency for good, and repaired the already-corrupted
  `Item.last_purchase_rate` master-data value on the live site.
- **Honest scope, stated plainly (also in the `branch_run` docstring):
  ERP state itself is NOT forked per branch.** Every branch's post-branch
  tool calls create real, permanent ERPNext documents in the SAME shared
  company — there is no per-branch isolated universe at the ERP layer
  (V2 §20's "scalable strategy" of per-branch site clones is not built).
  Verified directly: two branches of the same parent each create their
  own, distinct Purchase Order, but both reference the same shared
  `company`. Process/event-derived comparisons (paths, coherence,
  variety, actor continuity) are valid across branches since they derive
  purely from each branch's own events; comparisons against absolute
  shared ERP aggregates (e.g. "current stock level") are **not**, since
  multiple branches mutate the same underlying ledger concurrently.
- **Deviation:** `branch_run` requires the source run to already have an
  architecture name recoverable from its own snapshot (i.e. it was
  launched via `run_architecture`/`launch_pilot`, not `run_demo_episode`
  or `run_specialist_routine`) unless `architecture_name` is given
  explicitly — acceptable since every real experimental run goes through
  `run_architecture`.

---

## 7. SOTA Milestone 3 — Delivered

Real model provider + memory expansion (V2 §8.1, §14). Until this
milestone, **every single run in this entire project — all 8 original
milestones and both prior SOTA milestones — actually ran on
`DeterministicProvider`.** The provider abstraction existed since
Milestone 2's vertical slice, but the run loop hard-coded one shared
`DeterministicProvider()` instance for every actor regardless of what
each agent template's own `model_profile` said. No real model had ever
driven a single decision.

- **Per-agent provider resolution.** New `eorl_lab.providers.factory
  .get_provider_for_agent(agent)` reads the actor's OWN `EORL Model
  Profile.provider` field and dispatches accordingly
  (`deterministic` / `openai_compatible` / `anthropic` raises
  `NotImplementedError`, not yet built). `_run_episode_loop`,
  `_run_specialist_episode`, `_run_broad_autonomy_episode`, and
  `run_demo_episode` no longer construct or thread through a single
  shared provider — each actor slot resolves its own, so a
  `specialist_handoff` run can genuinely mix a real LLM-backed role
  with deterministic ones elsewhere in the same chain. Also fixed a
  small but real logging bug this surfaced: the `model_request` event
  hard-coded `payload={"provider": "deterministic"}` regardless of
  which provider actually ran.
- **`OpenAICompatibleProvider`** (`eorl_lab.providers.openai_compatible`):
  speaks the OpenAI chat-completions wire format — the lowest common
  denominator most self-hosted inference servers (vLLM, TGI, Ollama,
  LM Studio) and OpenAI itself all speak — using real function/tool
  calling (`tool_choice: "required"`), not JSON-in-prose parsing. Tool
  schemas are built by introspecting each registered tool's own Python
  signature, so the model only ever sees parameters a human operator
  would see; the orchestrator's framework-injected parameters
  (`_case`, `_sender_slot`, `_communication_policy`) are filtered out
  by name, never exposed. **Ground truth is never in the prompt** (V2
  §2.4): only the case's public fields, the actor's own accumulated
  `scratch`, and retrieved memory are shown — verified directly by a
  test that asserts the literal strings `latent_ground_truth`,
  `quality_probability`, etc. never appear in the constructed messages.
  New `finish_turn` tool (`eorl_lab.organization.control`) gives a
  model-driven actor an explicit, authority-governed way to decide
  *when* its turn is done — `DeterministicProvider` never needed this
  (it bundles `stop=True` onto its own last scripted action), but a
  model choosing actions turn-by-turn needs a real tool for it, subject
  to the same `EORL Tool Policy` allow-list as everything else.
- **Wired to a real, already-hosted model**, not a hypothetical one: a
  Qwen3 model (`barrydeen/Qwen3.8-27B-AWQ-4bit`) served via vLLM on a
  tailnet host, reachable from agrim's dev container. The API key lives
  in `site_config.json` only (`qwen_api_key`, via `bench set-config`),
  resolved through `EORL Model Profile.api_key_reference` — never
  stored on the DocType itself, never committed, never logged.
- **Live-verified end to end**, not just unit-tested: a real episode
  (`RUN-00083`, seed 55) where the Qwen3 model, with zero scripted
  guidance beyond its system prompt and tool schemas, autonomously
  chose and executed the full sequence itself — `get_supplier_options`
  → `create_purchase_order` → `submit_purchase_order` →
  `create_purchase_receipt` → `submit_purchase_receipt` →
  `inspect_received_goods` → `create_purchase_invoice` →
  `submit_purchase_invoice` → `create_payment_entry` →
  `submit_payment_entry` → `finish_turn` — producing a real, correctly
  priced (`grand_total: 492.0`) ERPNext Purchase Order chain, end to
  end, with no human or scripted logic choosing the sequence. 12 new
  tests in `test_eorl_llm_provider.py` cover provider-factory dispatch
  (deterministic/openai_compatible/unimplemented/disabled), the
  ground-truth-never-in-prompt guarantee, tool-schema filtering, and
  this exact live episode as an integration test hitting the real
  external endpoint (not mocked, by design — consistent with every
  other milestone's verification standard in this project). **69/69
  tests pass** (52 existing + 11 unit + 1 live integration — Qwen tests
  land in the same module as everything else since `finish_turn`
  changed in the process).
- **Real bugs found and fixed along the way, both load-bearing for any
  real provider (scripted or model-driven), not just this one:**
  - *Pricing.* The exact same fragile ERPNext `last_purchase_rate`
    self-reference SOTA Milestone 2 patched around for
    `DeterministicProvider` broke again the moment a real caller (the
    model) legitimately didn't know to pass `rate` — it has no
    legitimate way to know a hidden price. Fixed properly this time, at
    the root: `eorl_lab.erp.buying.create_purchase_order` now resolves
    `rate` from the scenario's own `latent_ground_truth[supplier].price`
    via the already-injected `_case` parameter when the caller doesn't
    supply one — server-side, transparent to whoever is calling,
    exactly like a real supplier-quoted price would be. No caller,
    scripted or model-driven, present or future, can trip this again.
  - *Uncaught provider failures.* `_run_actor_turn` wrapped tool
    execution in try/except (an organizational-process failure, not a
    crash — spec §9/28) but never wrapped `provider.generate()` itself.
    A real network-calling provider can fail in ways
    `DeterministicProvider` never could (timeout, malformed tool call,
    no tool call returned at all); now caught and logged as an `error`
    event + episode failure, the same way a bad tool call already was.
  - *Reasoning-budget starvation.* Qwen3 is a "thinking" model that can
    spend its entire `max_tokens` budget reasoning and return
    `finish_reason="length"` with no tool call at all. `EORL Model
    Profile.reasoning_mode_if_supported = "disabled"` (an existing,
    previously-unused field) now maps to the vLLM/Qwen3
    `chat_template_kwargs: {"enable_thinking": false}` convention —
    empirically, thinking *enabled* was actually more reliable for this
    multi-step procedure (a quick empirical check with thinking
    disabled made the model skip straight to `get_purchase_order` with
    a hallucinated document name instead of creating one first), so the
    live test runs with thinking on; the kill switch exists for
    cheaper/faster single-tool-call use cases that don't need it.
- **Semantic and procedural memory** (`eorl_lab.memory.semantic`,
  `eorl_lab.memory.procedural`), the two V2 §14 backends named
  alongside episodic but never built (`shared`/`vector` remain P2,
  unchanged). Both are real `EORL Memory Record` rows, not a new
  doctype — `EORL Memory Profile.local_backend` gained `semantic` and
  `procedural` options.
  - *Semantic* consolidates repeated observations about a stable
    SUBJECT (e.g. a supplier) into exactly one record per (run, actor,
    domain, subject), upserted rather than appended — `salience` holds
    the running success rate. The per-episode `case_summary` the
    orchestrator normally writes isn't a stable subject (every episode
    has a different case id), so this derives the real subject from
    the action string itself (`"ordered_from:X"` → subject `"supplier:X"`).
  - *Procedural* holds a single reinforced habit per (run, actor,
    domain): repeating the same successful action strengthens it
    (`salience` climbs toward 1.0); a genuinely different action resets
    it to a fresh, weak habit rather than blending the two.
  - 9 new tests in `test_eorl_memory_expansion.py` verify consolidation,
    distinct-subject separation, salience-ranked retrieval, habit
    reinforcement, and habit reset-on-change — all via direct
    `MemoryStore` calls, no LLM required (these are pure logic, not
    dependent on which provider is writing to them).
- **Deviations / honest limits:**
  - `OpenAICompatibleProvider` takes only the FIRST tool call if a
    model returns more than one in a single response (`tool_calls[0]`)
    — consistent with the "call exactly one tool per turn" instruction
    in the prompt, but not enforced beyond that instruction.
  - Confidence is a fixed placeholder (`0.7`) on every
    `OpenAICompatibleProvider` decision; this provider does not yet
    elicit a calibrated confidence score from the model.
  - Only one real provider engine is implemented
    (`openai_compatible`); `anthropic` is a real, selectable
    `EORL Model Profile.provider` option but still raises
    `NotImplementedError` — unchanged from the gap this milestone was
    scoped to close only for an OpenAI-compatible endpoint.
  - `shared` and `vector` memory backends remain unimplemented (V2 §32.2
    calls both P2); only `semantic` and `procedural` (P1) were built
    this milestone.

---

## 8. SOTA Milestone 4 — Delivered

Construct Registry + Experiment Builder expansion (V2 §20, §28.7).

- **`EORL Construct`**, a real standalone DocType (not a child table) —
  "a reusable library connecting theory to implementation" per spec
  wording. `construct_name`, `theoretical_definition`,
  `level_of_analysis`, `source_citations`, `computational_definition`,
  `manipulation_strategy`, `measurement_function`, `required_events`,
  `validity_notes`, `version` — every field the spec names. A
  controller method, `resolve_measurement_function()`, makes the
  "theory-to-implementation" link real and testable: it calls
  `frappe.get_attr()` on the dotted path and raises `NotImplementedError`
  loudly if the construct has none configured, rather than silently
  claiming a capability that doesn't exist.
- **All 8 "initial constructs" the spec names are seeded** (via a real
  Frappe patch, `eorl_lab.patches.v1_seed_initial_constructs`, so a
  fresh install gets them automatically on `bench migrate` — not a
  one-off script I ran and forgot). **Honest finding, stated rather
  than glossed over: only 2 of the 8 (Routine coherence, Adaptive
  repertoire) have a real, working `measurement_function` today** —
  `eorl_lab.analysis.coherence.actor_continuity` and
  `eorl_lab.analysis.repertoire.viable_path_entropy` respectively, both
  verified by a test that actually calls the resolved function against
  a real run's events. The other 6 (Centralization, Specialization,
  Formalization, Information asymmetry, Hierarchy, Transactive memory)
  are seeded with `measurement_function` **deliberately left blank**
  and an honest `validity_notes` explaining exactly what's missing —
  in Transactive memory's case, that there is no expertise-belief
  modeling anywhere in the system at all, not just a missing metric
  function. The registry's value is in being a truthful map of
  theory-to-implementation as it stands today, not an aspirational one.
- **`EORL Experiment Factor`** (new child table) + `EORL
  Experiment.factors` generalize the fixed `architecture_a` /
  `architecture_b` pair into a real N-factor, K-level factorial
  design — **without changing the original behavior at all**: when
  `factors` is empty, `cell_count()`, `total_run_count()`,
  `validate_experiment`, and `launch_pilot` all take the exact original
  Milestone 6 code path, byte-for-byte (verified directly by a test
  using the OLD architecture_a/architecture_b fixture shape, asserting
  `factorial_cells() == []` and the old arithmetic). When `factors` has
  rows, `launch_pilot` runs the full cartesian product of every
  distinct `factor_name`'s levels — live-verified with a real 2×2
  design (coordination structure × regime shift) producing 4 real runs,
  each resolving the right architecture/regime-shift combination, with
  `seed_strategy: paired` giving every cell in a repetition the
  identical seed (V2 §18) exactly as the 1-factor path already did.
  **Honest scope:** factor levels are limited to `architecture` and
  `regime_shift` — the two independent knobs `run_architecture()`
  actually exposes. Varying model/memory profile as a factor isn't
  possible independently of architecture (an `EORL Architecture`'s
  `actor_slots` bind specific agent templates with baked-in profiles),
  so that's expressed by making architecture itself the factor
  (different architectures pointing at agent templates with different
  model profiles) rather than inventing unsupported runtime behavior.
- **`EORL Experiment.focal_construct`** (optional `Link` to `EORL
  Construct`) — V2 §21's Theory Compiler names "focal theoretical
  construct" as its first researcher input; this is that link, without
  building the full wizard (still a later milestone).
- **Ablation marking** (V2 §19: *"Provide an interface for marking a
  run as an ablation of another configuration."*) — read literally, as
  a thin interface, not a new engine. `EORL Run` gained
  `is_ablation_of` (Link to `EORL Run`) and `ablation_mechanism`
  (text), set via the new whitelisted `eorl_lab.api.runs.mark_ablation`,
  which also emits a real `run_marked_ablation` event. Deliberately
  independent of `branch_run()`'s shared-history lineage from SOTA
  Milestone 2 — an ablation is a separate full run with one mechanism
  toggled, not required to share any episodes with its baseline, which
  matches the spec's own ablation examples (memory/tool/communication
  ablation as separate complete runs compared against a baseline, not
  branches of it).
- 15 new tests (`test_eorl_construct_registry_and_factorial_experiments.py`)
  cover: all 8 constructs seeded; the 2 implemented ones resolve to a
  real callable and actually run against real event data; an
  unimplemented one raises `NotImplementedError` rather than silently
  returning something; the 1-factor/2-level backward-compatibility
  guarantee; cell-count arithmetic for a 2×2 design; a full live
  `launch_pilot` across all 4 cells with correct architecture/regime
  resolution and paired seeding; `focal_construct` validation (valid
  and invalid); invalid architecture inside a factor row;
  `mark_ablation`'s success path, its emitted event, and its two
  rejection paths (unknown baseline, self-reference). **84/84 tests
  pass** (69 existing + 15 new; the live Qwen integration test from
  SOTA Milestone 3 continues to run and pass as part of the same app
  test suite).
- **Deviations / honest limits:**
  - No queued/background execution for large factorial designs —
    `launch_pilot` still runs every cell × repetition synchronously
    within the request (the same Milestone 6 deviation as before;
    Milestone 9's scope, unchanged).
  - The Theory Compiler wizard (V2 §21) is not built; `focal_construct`
    is a link field, not a structured intake flow.
  - The Mechanism/Ablation Dashboard (V2 §43) that would actually
    *consume* `is_ablation_of`/`ablation_mechanism` visually is not
    built — this milestone is the marking interface only, as the spec
    literally asked for.
  - `shared`/`vector` memory backends and 6 of the 8 constructs'
    measurement functions remain unimplemented, unchanged from prior
    milestones' honest gaps.

---

## 9. SOTA Milestone 5 — Delivered

Analytics workbench, phase 1 (V2 §44, §55's P0 slice).

- **A real statistics engine** (`eorl_lab.analysis.stats`), thin
  wrappers around `scipy.stats` rather than hand-rolled numerics.
  **Deviation from how this milestone started:** the first pass
  hand-rolled Student's t CDF/PPF and a permutation test from scratch
  in pure Python (to avoid adding a dependency). The t-distribution
  implementation was verified correct against known values, but the
  hand-rolled permutation test had a real, reproducible bug — it
  converged to p≈0.048 against an exact-enumeration reference value of
  p≈0.056 on a classic textbook dataset, confirmed via brute-force
  enumeration of all C(12,6)=924 relabelings. Switched to `scipy.stats`
  instead of continuing to debug it, which immediately matched the
  exact-enumeration value. `scipy` (and `numpy`) are now real,
  declared dependencies (`pyproject.toml`) — there was no good reason
  to keep reinventing well-tested numerical primitives.
  - `welch_t_test`, `permutation_test`, `hedges_g` for two independent
    conditions (V2 §44.4); `paired_t_test`, `paired_permutation_test`,
    `paired_hedges_g` for matched/paired conditions (V2 §44.3).
  - `welch_t_test` reproduces the classic unequal-variance textbook
    example exactly (t=1.959, df=7.03, p=0.0908 — also matches what R's
    `t.test()` or calling scipy directly report for the same data).
- **`EORL Analysis Plan`** (V2 §44.1): every field the spec names,
  including several explicitly marked as **reserved/not read yet** in
  their own field descriptions (`formula`, `covariates`,
  `multiple_testing_family`, `equivalence_bounds`,
  `bootstrap_iterations` — all P1, section 44.4's model-based test
  families and section 45.1's equivalence testing) rather than quietly
  ignored. `analysis_unit` (default `"run"`) is the field the
  independence guardrail actually reads.
- **The independence guardrail is enforced, not documented** (V2 §44.2,
  visualization acceptance test 54.3): `eorl_lab.api.analysis
  .compare_groups` — the only entrypoint in this app that runs a
  between-condition statistical comparison — refuses outright to run
  when `analysis_plan.analysis_unit != "run"`. There is no honest
  "require explicit hierarchical specification" fallback built yet (no
  mixed-effects/GEE model exists — that's P1), so this takes
  54.3's **"block the analysis"** branch, not the alternative one. Every
  outcome value `compare_groups` reads is one persisted, run-level
  `EORL Metric` row (computing it via `compute_run_metrics` if not
  already there) — never a per-episode value.
- **"Recommend, never silently select" is structural, not a UI
  affordance** (V2 §44.4): `compare_groups` always computes AND
  persists **both** the parametric and the distribution-free test for
  whichever pairing mode applies (`welch_t` + `permutation`, or
  `paired_t` + `paired_permutation`) — there is no code path that
  returns only one.
- **Paired-branch verification, not trust** (V2 §44.3): setting
  `EORL Analysis Plan.paired_by` doesn't just change which test runs —
  `compare_groups` *verifies* every `(group_a[i], group_b[i])` pair
  actually shares the same `parent_run` and `branch_point_episode`
  (SOTA Milestone 2's lineage fields) before treating them as matched,
  and throws rather than silently falling back to an independent-groups
  test if a claimed pair isn't a genuine sibling-branch pair.
- **`EORL Analysis Result`** (V2 §52): one row per test family per
  comparison, naming the exact run IDs in both groups, N independent
  runs *and* N episodes (never conflated), the metric version, the
  `scipy` version that computed it, and the full raw result as JSON —
  "a user should be able to click any reported result and see exactly
  which runs generated it" is satisfied via ordinary Frappe Link-field
  navigation (consistent with how Architectures/Agent Templates are
  still composed via plain DocType forms rather than a bespoke wizard),
  not a custom provenance viewer.
- **Live-verified with a real, substantively meaningful comparison**:
  5 `broad_autonomy` runs vs. 5 `specialist_handoff` runs (3 episodes
  each), comparing `actor_continuity`. Broad autonomy's continuity is
  **exactly 1.0 for every run** (architecturally guaranteed — one actor
  does everything), specialist handoff's mean was 0.713 with real
  variance across runs. Welch's t: t=99.0, df=4, **p=6.2×10⁻⁸**;
  permutation test (5000 resamples): **p=0.0079** — two structurally
  different test families agreeing the effect is real. Both results
  landed as real `EORL Analysis Result` rows with correct provenance.
- **Scientific Cockpit** (V2 §38, scoped to its KPI-card core): a new
  desk page (`/app/eorl-scientific-cockpit`) — pick a saved Analysis
  Plan and two groups of runs, compare, see independent-N /
  episode-N / means / standardized effect as KPI cards, both test
  families' p-values and CIs in a table, each with a click-through link
  to its full `EORL Analysis Result` record.
- **Added a `success_rate` run-level metric** to
  `eorl_lab.api.metrics.compute_run_metrics` — previously only computed
  ad hoc, inline, by the Compare Runs page; now a real persisted named
  metric any Analysis Plan can target as its `outcome_metric`.
- **A real platform edge case found and fixed**: `scipy`'s Welch's
  t-test legitimately returns `nan` when both groups have zero
  variance (e.g. every run in both groups succeeded every episode) —
  MySQL rejects `NaN`/`Inf` outright for a Float column. Fixed with a
  `_clean_float` helper that converts them to `NULL` before the
  `EORL Analysis Result` is saved — `NULL` ("undefined") is also the
  scientifically correct representation here, not a fabricated number.
- **Deviations / honest limits, stated plainly:**
  - **Process Explorer (DFG + episode swimlane), adaptation trajectory,
    and run-level distribution comparison as dedicated graphical pages
    are NOT built this milestone.** The underlying data for all three
    already exists and is reachable today (`directly_follows_graph` is
    a real persisted `EORL Metric`; per-episode outcome/phase data is
    on `EORL Episode`; distributions are the `values_a`/`values_b` any
    `compare_groups` call already computes) — only the bespoke
    graphical/cross-filtering UI wrapping them is deferred, consistent
    with this project's established pattern of shipping real data and
    plain DocType/table access before a bespoke visual designer (Agent
    Studio, Architecture Designer, and Scenario Studio are deferred the
    same way).
  - Mann-Whitney U and Wilcoxon signed-rank (both named in V2 §44.4 as
    "robustness" additions, not the P0 bullet list itself) are not
    implemented.
  - No multiple-testing correction (V2 §46) and no TOST equivalence
    testing (V2 §45.1) — both explicitly P1/P2.
  - No mixed-effects/GEE/clustered model exists, so `analysis_unit`
    has exactly one honest setting (`"run"`) today; `"episode"` is a
    real selectable option that `compare_groups` always refuses.
  - Cross-filtering between panels (visualization acceptance test 54.1)
    doesn't apply yet — there is only one panel (the Cockpit's own
    compare form), not yet multiple linked visualizations.

---

## 10. Next: SOTA Milestone 6 (analytics workbench, phase 2 / P1) or beyond

SOTA Milestones 1–5 closed the structural gaps, delivered counterfactual
branching, replaced the all-deterministic run loop with a real,
live-verified model provider and two new memory backends, generalized
the Experiment Builder into a real factorial design with a
theory-to-implementation Construct Registry and ablation marking, and
delivered a real, scipy-backed statistical inference engine with an
enforced independence guardrail and trace-linked result provenance. The
roadmap in section 4 above (and V2 §55's P1 list) covers what comes
next: mixed-effects longitudinal models, paired-branch inference UI,
equivalence tests, the event-study/adaptation-trajectory view, the
Process Explorer / network explorer graphical pages, a robustness
forest plot, replication-stability diagnostics, and publication table
export. Confirm before continuing further, same as before starting
Milestones 1 through 5.
