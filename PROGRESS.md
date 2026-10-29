# EORL Lab — Build Progress

This documents what has actually been built, tested, and run against real
data so far, against the build order in `EORL_LAB_AGENT_BUILD_SPEC.md`
(section 26). It is a working log, not a promise of what the spec
eventually asks for — every deviation from the spec is called out
explicitly where it happens, per the spec's own instruction (section 31:
"document the deviation and its scientific consequences rather than
silently changing the design").

Repo: https://github.com/agrimsachdeva/eorl_lab (private)
Installed on: `erpnext.localhost` site, alongside `erp_research`, on the
dev-mode bench at `~/frappe_docker/development/frappe-bench` on `agrim`
(Docker Compose stack: `mariadb`, `redis-cache`, `redis-queue`, `frappe`
containers — see `~/frappe_docker/.devcontainer/docker-compose.yml`).

---

## How to run things

```bash
# enter the dev container
docker exec -it devcontainer-frappe-1 bash
cd /workspace/development/frappe-bench
source env/bin/activate

# run the full test suite
bench --site erpnext.localhost run-tests --app eorl_lab

# run one demo episode (Milestone 2, single actor)
bench --site erpnext.localhost execute eorl_lab.runtime.orchestrator.run_demo_episode \
  --kwargs '{"agent_template_name": "Demo Purchasing Agent", "seed": 42}'

# run the four-agent specialist routine (Milestone 3/4), N episodes
bench --site erpnext.localhost execute eorl_lab.runtime.orchestrator.run_specialist_routine \
  --kwargs '{"agent_templates": {"purchasing_agent": "Demo Purchasing Agent", "purchasing_manager_agent": "Demo Purchasing Manager Agent", "warehouse_agent": "Demo Warehouse Agent", "accounts_payable_agent": "Demo Accounts Payable Agent"}, "seed": 42, "episode_count": 3}'

# run either architecture by name (Milestone 5, config-driven)
bench --site erpnext.localhost execute eorl_lab.runtime.orchestrator.run_architecture \
  --kwargs '{"architecture_name": "Demo Specialist Handoff", "seed": 123, "episode_count": 3, "regime_shift": "Demo Demand Shock"}'
bench --site erpnext.localhost execute eorl_lab.runtime.orchestrator.run_architecture \
  --kwargs '{"architecture_name": "Demo Broad Autonomy", "seed": 123, "episode_count": 3, "regime_shift": "Demo Demand Shock"}'
```

Browse results in the Desk at `erpnext.localhost:8000/app/eorl-run`,
`/app/eorl-episode`, `/app/eorl-event`, `/app/eorl-memory-record`.

---

## Milestone 1 — App skeleton and config

**Delivered:**
- `eorl_lab` installed as a separate Frappe app on `erpnext.localhost`,
  alongside `erp_research` (per spec section 1 — same site, no dependency
  on the legacy app).
- Roles: `EORL Researcher`, `EORL Administrator`, `EORL Viewer` (fixture,
  `eorl_lab/fixtures/role.json`).
- DocTypes: `EORL Settings` (single), `EORL Model Profile`,
  `EORL Memory Profile`, `EORL Tool Policy` (+ child `EORL Allowed Tool`),
  `EORL Agent Template`. Fields match spec section 6.1–6.5. Secrets are
  stored as references only (`api_key_reference`,
  `external_worker_callback_secret_reference`), never plaintext.
- One Desk page, `/app/eorl-lab`, placeholder-level: links to the config
  list views, notes that the research-studio pages don't exist yet.
- 2 tests (DocType access + a cross-doctype binding integration test).

---

## Milestone 2 — Vertical slice

**Delivered:**
- `eorl_lab/providers/` — `ModelProvider` ABC (`ModelRequest`,
  `ModelResponse`) and `DeterministicProvider`, a rule-based provider for
  tests/demos (spec section 8.1).
- `eorl_lab/runtime/authority.py` — `evaluate()`, the authority firewall
  (spec section 9): checks a tool call against the actor's own
  `EORL Tool Policy.allowed_semantic_tools`, outside the model, always.
- `eorl_lab/erp/` — semantic tool registry + two tools:
  `get_supplier_options` (read), `create_purchase_order` (write, creates
  a real, unsubmitted ERPNext Purchase Order).
- `eorl_lab/scenarios/procurement.py` — one deterministic case, fixed
  against real master data (`Hoosier Ice Cream` / `MILK-001` /
  `Bloomington Dairy`, `Indiana Foods Inc`).
- `eorl_lab/observability/` — `ExperimentContext` (trace/span/correlation
  propagation, spec section 16.1) and `emit_event()`.
- DocTypes: `EORL Run`, `EORL Episode`, `EORL Event` (append-only — the
  controller rejects edits and deletes unconditionally, not just "after
  the run completes").
- `eorl_lab/runtime/orchestrator.py::run_demo_episode` — the actual
  decide → authorize → execute → observe loop.
- **Deviation:** `EORL Run` omits `experiment`/`cell_id`/`repetition`
  (spec section 6.10) because `EORL Experiment` doesn't exist yet
  (Milestone 6). Filled in once it does.
- Verified live (not just tests): created real Purchase Order
  `PUR-ORD-2026-00446` against `Bloomington Dairy`, 22-event trace,
  zero gaps. A second test proves an out-of-policy tool request is
  denied (`TOOL_NOT_IN_POLICY`) and produces no ERP mutation.

---

## Milestone 3 — Multi-agent routine

**Delivered:**
- Four persistent actor slots: Purchasing Agent, Purchasing Manager
  Agent, Warehouse Agent, Accounts Payable Agent — each bound to its own
  `EORL Tool Policy` restricting exactly its tools.
- Full procure-to-pay chain: `submit_purchase_order`,
  `create_purchase_receipt`, `submit_purchase_receipt`,
  `create_purchase_invoice`, `submit_purchase_invoice`,
  `create_payment_entry`, `submit_payment_entry` — all via ERPNext's own
  `make_purchase_receipt` / `make_purchase_invoice` / `get_payment_entry`
  mapper functions, so tax/account/UOM resolution matches what a human
  user's "Make >" button would produce.
- `_handoff()` — explicit, logged inter-agent messages
  (`agent_message_sent`/`agent_message_received`) between every
  consecutive stage. For this architecture the handoff topology is
  enforced by the orchestrator, not left to agent choice (spec section
  2.3 Architecture A: "explicit handoffs ... limited cross-stage
  autonomy" is structural, not a prompt instruction).
- Authority firewall gained a second independent rule:
  `may_submit_documents` is enforced regardless of tool-registry
  membership. Tested: a Purchasing Manager Agent without submit rights
  is denied (`SUBMIT_NOT_PERMITTED`) and the routine halts with only a
  draft PO — no receipt/invoice/payment.
- Refactored Milestone 2's loop into a shared `_run_actor_turn()` so both
  milestones' orchestration is one implementation, not two.
- **Deviation:** the scenario's `candidate_suppliers`/
  `latent_ground_truth` fields aren't yet driving agent choice — the
  Purchasing Agent still queries live `get_supplier_options` and the
  ground-truth-driven probabilistic outcomes (spec section 11) are not
  implemented. Honest gap, not hidden.
- Verified live: PO `PUR-ORD-2026-00447` → Receipt `MAT-PRE-2026-00418`
  → Invoice `ACC-PINV-2026-00217` → Payment `ACC-PAY-2026-00109`, all
  four **submitted** (docstatus 1), 119 events.

---

## Milestone 4 — Memory and repeated episodes

**Delivered:**
- `eorl_lab/memory/` — `MemoryStore` ABC, `NoMemoryStore`,
  `RecentMemoryStore`, `EpisodicMemoryStore` (weighted recency + outcome
  scoring, using the `EORL Memory Profile.recency_weight`/
  `outcome_weight` fields that had sat unused since Milestone 1), and a
  `get_memory_store()` factory. `shared`/`vector` backends raise
  `NotImplementedError` with a clear message (out of scope until a
  shared-memory architecture / embedding profile exists).
- DocType: `EORL Memory Record` (spec section 14 schema).
- `run_specialist_routine()` gained `episode_count`: repeated episodes
  within one run, each with a fresh deterministically-varying case
  (`generate_case(seed, episode)` cycles quantity 500–750 as a pure
  function of `(seed, episode)` — reproducible, not random).
- Memory is wired as an explicit per-actor condition: every actor's turn
  retrieves memory (even if empty) and writes a record after, both
  logged (`memory_query`/`memory_retrieval`/`memory_write`) regardless of
  whether a memory profile is even configured — "no memory" is a logged
  condition, not a skipped step.
- Run-start snapshotting of bound agent templates into
  `EORL Run.agent_snapshots_json` (spec section 8.4).
- **Verified causally, not just correlationally:** ran 3 live episodes.
  Episode 1's Purchasing Agent had no memory and picked a supplier by
  default. Episodes 2–3 **explicitly cite**
  `"repeat a remembered successful supplier choice (routinization)"` in
  their own logged decision — checked the decision's stated basis, not
  just that the outcome matched (which could have been coincidence,
  since the underlying read tool's result order is already stable
  regardless of memory).

---

## Milestone 5 — Architectures and shock

**Delivered:**
- DocTypes: `EORL Architecture` (+ child `EORL Architecture Actor Slot`),
  `EORL Regime Shift`.
- `run_architecture(architecture_name, seed, episode_count, regime_shift)`
  — the real config-driven entrypoint. Reads `coordination_mode` from
  the document and dispatches; **the caller never names a Python
  function per architecture.**
- Architecture B (broad autonomy): one `General Purchasing Agent` walks
  the entire chain itself, zero handoffs, using the *same*
  `_choose_supplier()` decision rule as the specialist Purchasing Agent
  (shared helper) — so the two architectures are comparable in what they
  attempt, differing only in organizational structure.
- Regime shift: `generate_case(seed, episode, regime_shift)` applies a
  deterministic demand shock (`qty_multiplier`) starting at
  `trigger_episode`, never exposed to the agent as a "something changed"
  signal — only the ordinary `qty` value changes (spec section 2.4,
  `hidden_from_agents`).
- **Deviation:** `EORL Architecture`'s supervision/communication/
  handoff-rule/escalation/approval fields are plain JSON for now — the
  orchestrator reads only `coordination_mode` and `actor_slots`. They
  become real editable graphs with the Architecture Designer (Milestone
  6's front end).
- Implemented a scoped version of spec section 30's acceptance test:
  fixed shocked stream, both architectures on the same seed, scenario
  hashes/quantities identical pre- and post-shock, process genuinely
  different (actor-identity cardinality, event counts) — without the
  metrics/export layers (Milestones 7/8), which don't exist yet.
- **Verified live:** both architectures, seed 123, 3 episodes, demand
  shock at episode 2 (`qty_multiplier: 1.8`). Both received *identical*
  quantities every episode (700 → 1350 → 900). Event counts differ as
  expected (389 specialist vs. 323 broad-autonomy).

---

## Test coverage so far

11 tests, all green, spanning Milestones 1–5:
- `test_eorl_settings.py`, `test_eorl_agent_template.py` (M1)
- `test_eorl_run.py` (M2, incl. an authority-denial test)
- `test_eorl_multi_agent_routine.py` (M3, incl. a submit-rights-denial
  test)
- `test_eorl_memory_and_repeated_episodes.py` (M4, incl. a
  memory-causality test and a no-memory-profile test)
- `test_eorl_architectures_and_shock.py` (M5, incl. the paired-seed/shock
  acceptance test)

Run: `bench --site erpnext.localhost run-tests --app eorl_lab`

---

## What's explicitly NOT built yet (honest gap list)

- `EORL Experiment`, `EORL Scenario` DocTypes — Milestone 6's Experiment
  Studio needs the former; the full distributional scenario generator
  (section 11) needs the latter. The current generator is a fixed case
  with deterministic quantity variation, not a configurable distribution.
- Any front-end beyond the Milestone 1 placeholder page — Experiment
  Studio, Agent Studio, Architecture Designer, Scenario Studio, Run
  Monitor, Trace Explorer, Compare Runs, Export/Reproducibility (spec
  section 7) are all Milestone 6.
- Process-path extraction and theory metrics (coherence, repertoire,
  entropy, recovery curves — spec section 17) — Milestone 7.
- One-click reproducibility export/import (JSONL/CSV/YAML bundle,
  section 18) — Milestone 8.
- External/HPC worker execution, Parquet export, isolated concurrent
  environments (section 20) — Milestone 9.
- Inter-agent communication is currently orchestrator-enforced handoffs
  only — agent-initiated `message_agent`/`request_approval`/
  `escalate_exception` tool calls (section 10's communication tools)
  aren't implemented; they become relevant once an architecture lets
  agents choose to communicate rather than following a fixed topology.
- `erp_research` migration/parity work (section 25 Phase A–D) hasn't
  started — nothing has been reused from the legacy app yet, which is
  fine (not required), but also not yet verified.

---

*Last updated: end of Milestone 5.*
