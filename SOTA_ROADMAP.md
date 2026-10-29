# EORL SOTA Roadmap

**Status:** SOTA Milestone 1 delivered. Created 2026-10-29, updated 2026-10-29
(SOTA M1).

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

## 6. Next: SOTA Milestone 2 (counterfactual branching) or beyond

SOTA Milestone 1 closed the structural gaps that blocked everything
downstream. The roadmap in section 4 above still applies for what comes
next (counterfactual branching → memory expansion/real LLM provider →
Construct Registry/Experiment Builder expansion → analytics workbench
phase 1). Confirm before continuing further, same as before starting
Milestone 1.
