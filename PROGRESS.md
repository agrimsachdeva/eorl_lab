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

# validate and launch a full EORL Experiment pilot (Milestone 6)
bench --site erpnext.localhost execute eorl_lab.api.experiments.validate_experiment \
  --kwargs '{"experiment_name": "Demo Adaptive Repertoire Pilot"}'
bench --site erpnext.localhost execute eorl_lab.api.experiments.launch_pilot \
  --kwargs '{"experiment_name": "Demo Adaptive Repertoire Pilot"}'
```

Browse results in the Desk at `erpnext.localhost:8000/app/eorl-run`,
`/app/eorl-episode`, `/app/eorl-event`, `/app/eorl-memory-record`, or through
the Studio pages: `/app/eorl-lab`, `/app/eorl-experiment-studio`,
`/app/eorl-run-monitor`, `/app/eorl-trace-explorer`, `/app/eorl-compare-runs`,
`/app/eorl-reproducibility`.

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

## Milestone 6 — Research front end

**Delivered:**
- DocType: `EORL Experiment`. **Deviation:** supports exactly the
  one-factor, up-to-two-level design (`architecture_a` vs
  `architecture_b`) Milestones 2–5 were built around, not a general
  N-factor factorial table with explicit cell definitions (spec section
  6.9). `cell_count()`/`total_run_count()` generalize trivially once a
  real factor table exists; they don't today.
- `eorl_lab/api/experiments.py` — `get_experiment_summary`,
  `validate_experiment`, `launch_pilot` (runs synchronously within the
  request for a small pilot, not queued as a background job — queued
  execution is Milestone 9's scope). `launch_pilot` honors
  `seed_strategy`: `paired` gives `architecture_a`/`architecture_b` the
  same seed per repetition; `independent` offsets by architecture index.
- `eorl_lab/api/traces.py`, `eorl_lab/api/metrics.py`,
  `eorl_lab/api/exports.py` — read-only APIs over the existing
  Run/Episode/Event/Memory-Record tables; nothing new is computed beyond
  what Milestones 2–5 already wrote.
- Five Desk pages, all functional (not mockups), backed by the APIs
  above:
  - `/app/eorl-experiment-studio` — pick a saved `EORL Experiment`,
    see the computed cell/run count, Validate Only / Launch Pilot.
    **Deviation:** experiments/architectures/agents are composed via
    their ordinary DocType forms (linked from this page), not the full
    10-step wizard of spec section 7.5.
  - `/app/eorl-run-monitor` — polls every 5s, status pill, click-through
    to Trace Explorer.
  - `/app/eorl-trace-explorer` — run → episode → chronological event
    table, with event-type/actor/failures-only filters, expandable
    payloads. The page spec calls "essential for auditability"; it
    reads directly off `EORL Event`, nothing is pre-aggregated or
    summarized away.
  - `/app/eorl-compare-runs` — multi-select runs, side-by-side raw
    aggregates (episode/event counts, success rate, distinct-actor
    count). **Deviation:** no process-path/coherence/repertoire/entropy
    metrics yet (spec section 17) — that needs the process-path
    extraction layer, Milestone 7.
  - `/app/eorl-reproducibility` — pick a run, download a JSON bundle
    (manifest + episodes + events + memory records) via a client-side
    Blob download. **Deviation:** this is the raw-data half of spec
    section 7.9's bundle (no resolved prompts, no replayable scenario
    stream, no computed metrics, no one-click re-run) — the full
    reproducibility artifact is Milestone 8.
  - `/app/eorl-lab` (updated) — now links to all five pages above, not
    just the config DocTypes.
  - **Not built:** Agent Studio, Architecture Designer (graphical),
    Scenario Studio — all explicitly deferred; composing agents and
    architectures still goes through their plain DocType forms.
- One bug caught and fixed during this milestone: a test that tried to
  create an `EORL Experiment` with a dangling `Link` reference to prove
  `validate_experiment` catches it — Frappe's own link validation
  rejected the insert before my code ever ran. Fixed by constructing
  that edge case with `ignore_links=True` (simulating a regime shift
  deleted *after* being referenced, which Frappe's own validation
  doesn't protect against).
- **Verified live, not just tested:** created a real `EORL Experiment`
  ("Demo Adaptive Repertoire Pilot": both architectures, the Milestone 5
  demand shock, 2 repetitions, paired seeds, base seed 777) and launched
  it through the actual API. All 4 runs succeeded; repetition 0 used
  seed 777 for *both* architectures, repetition 1 used seed 778 for
  *both* — the pairing held under the real multi-run launch path, not
  just a two-run test. Then exercised Compare Runs and Export against
  those same real runs: `compare_runs` correctly reported 4 vs. 1
  distinct actors at 100% success each; `export_run_bundle` returned the
  full 3-episode, 323-event bundle for the broad-autonomy run.
- Note on verification scope: I did not drive these pages through an
  actual browser (no Playwright/browser automation set up for this
  project). I verified every whitelisted API function directly via
  `bench execute` and via the test suite, and reviewed the JS by hand —
  but the rendered pages themselves are unverified by me. Worth a manual
  look before relying on them.

## Milestone 7 — Process representation and theory metrics

**Delivered:**
- DocType: `EORL Metric` (spec section 6.13, listed since the original
  spec but not actually needed until now).
- `eorl_lab/analysis/` — `paths.py` (canonical action events, spec
  section 17.1, and the 8-stage mapping from section 17.2),
  `sequence.py` (unique sequence count, sequence/transition entropy,
  modal-path share, directly-follows graph), `coherence.py` (actor/
  functional/stage continuity and switch rates, average actor run
  length, repeated-path probability), `repertoire.py` (viable-path
  definitions with an explicitly versioned viability criterion per
  spec's own instruction, breadth by exception family, reuse/novel/
  extinction around a shock, top-k concentration), `recovery.py`
  (post-shock drop, episodes-to-recover, area-under-recovery-curve,
  post-shock error rate, change in entropy/concentration),
  `networks.py` (communication network from `agent_message_sent`
  events). **Every function takes plain dicts/lists shaped like
  `eorl_lab.api.exports.export_run_bundle`'s output — none of them
  query Frappe** (spec section 17's closing requirement: "All metric
  functions must accept raw exported events so they can be recomputed
  outside Frappe").
- `eorl_lab/api/metrics.py::compute_run_metrics(run_name)` — the only
  place that touches Frappe; fetches one run's episodes/events,
  derives per-episode paths, calls the pure functions, and persists
  each result as a versioned `EORL Metric` row. `compare_runs` (from
  Milestone 6) now also surfaces `unique_sequence_count`,
  `sequence_entropy`, `actor_continuity`, and `average_actor_run_length`
  inline. The Compare Runs page gained a "Compute & Persist Full Metric
  Set" panel.
- **An empirically-grounded, two-sided finding, not a one-sided success
  claim:** I checked, before writing any metric code, whether the
  existing deterministic policies actually vary their tool-call
  sequence across episodes — they don't. Every episode within a run
  follows byte-identical stage/tool order; only argument *values*
  (quantity, which supplier) differ. This means:
  - **Routine-variety metrics are real but currently vacuous**:
    `unique_sequence_count == 1` and `sequence_entropy == 0.0` on every
    run checked so far (verified on both the specialist and
    broad-autonomy runs from Milestone 6's real demo pilot) — not a bug,
    an honest consequence of the policies not branching yet.
  - **Coherence metrics genuinely discriminate architecture today**,
    verified on that same real data: specialist run `RUN-00006` —
    `actor_switch_rate = 0.314`, `actor_continuity = 0.686`,
    `average_actor_run_length = 3.0`. Broad-autonomy run `RUN-00007` —
    `actor_switch_rate = 0.0`, `actor_continuity = 1.0`,
    `average_actor_run_length = 33.0` (the whole 3-episode run is one
    unbroken actor identity). This is exactly the theoretical prediction
    from spec section 2.3, now actually measured, not just plausible.
  - Repertoire/adaptation metrics that depend on variety across phases
    (novel paths after shock, path extinction, post-shock performance
    drop) are also real and tested — proven correct on controlled
    synthetic fixtures with genuine drops/recoveries/novel paths — but
    return their vacuous values (0 drop, 0 novel paths, 100% reuse) on
    live data, because the current regime shift only changes quantity,
    never success/failure.
- 30 tests (16 new): synthetic unit tests proving every formula against
  hand-computed expected values on controlled fixtures (including a
  fixture with genuine performance drops/recoveries and genuine path
  extinction/novelty around a synthetic shock), plus integration tests
  that run the real orchestrator, call `compute_run_metrics` for real,
  and assert both the coherence discrimination *and* the variety
  vacuity — the test suite enforces the honest finding, it doesn't just
  happen to produce it once.

**What this means for the research question going forward:** the
adaptive-repertoire-paradox metrics (sections 2.2–2.3's whole point) will
show real signal only once either (a) a non-deterministic/LLM provider
introduces genuine path variation, or (b) the scenario generator's
exception families and ground-truth-driven outcomes (still not built —
Scenario Studio) make even a deterministic policy branch differently
under different conditions. The machinery to measure that signal, the
moment it exists, is now built and tested; it has nothing to measure yet.

---

---

## Milestone 8 — Reproducibility artifact

**Delivered:**
- `eorl_lab/observability/exporter.py` — builds the full spec section
  7.9 artifact set as an in-memory zip: `run_manifest.json`,
  `architecture.json`, `resolved_agent_configs/*.json` (one per actor
  slot), `scenario_stream.jsonl` (every episode's case, *regenerated*
  from the recorded seed/regime-shift via the same pure
  `generate_case()` Milestone 2 built — not read back from storage, so
  building the bundle doubles as a determinism check), `events.jsonl`
  (the complete raw event log), `process_paths.csv`, `metrics.csv`,
  `model_metadata.json` (no API keys), `environment_metadata.json`,
  `code_commit.txt`, `requirements_lock.txt`, `README_REPRODUCE.md`
  (templated with this run's actual seed/architecture/commit so the
  instructions are copy-pasteable, not generic).
- `eorl_lab/observability/replay.py::reproduce_run(run_name)` — reads
  an existing run's own recorded seed/architecture/regime-shift back
  out of its snapshot and `run_initialized` event (never asks the
  caller to re-supply them), launches a brand-new run through the same
  `run_architecture()` entrypoint any researcher would use, then
  verifies reproduction two ways: per-episode scenario **case-hash**
  equality (not just matching IDs, which are string-formatted from the
  inputs and would trivially "match" without proving anything) and
  exact numeric equality across every computed metric.
- `eorl_lab/api/exports.py::download_full_bundle` streams the zip as a
  native browser download (Frappe's file-response mechanism, not a
  JSON blob over the RPC channel — the bundle can be hundreds of KB).
  The Reproducibility page gained "Download Full Bundle (.zip)" and
  "Reproduce & Verify" actions alongside Milestone 6's quick JSON
  export.
- One real bug fixed along the way: `run_architecture`'s regime-shift
  snapshot stored the shift's *parameters* but not its *name* — meaning
  nothing could look the shift back up to replay it. Caught while
  writing `reproduce_run`, fixed by adding `"name"` to the snapshot.
- 33 tests (3 new): the zip's contents are asserted file-by-file
  (including that `model_metadata.json` never contains
  `api_key_reference`), `reproduce_run` is proven on a real
  `run_architecture` run (scenario hashes and metrics both match,
  confirmed to be a genuinely new, independent run with its own ERP
  documents), and a dedicated test proves `reproduce_run` *refuses* —
  rather than guesses — on a run launched through the older
  `run_specialist_routine` path that doesn't carry an architecture name.
- **Verified live, on a run from three milestones ago, not a fresh
  fixture:** built the full bundle for `RUN-00006` (the specialist-
  architecture run from Milestone 6's real demo pilot) — all 14 files
  present with real content, 37.7KB zip. Then called `reproduce_run` on
  that same pre-existing run: it launched brand-new run `RUN-00010`,
  reporting `scenario_stream_matches: true` and `metrics_match: true`.
  This is the milestone's whole claim — "one-click export and
  successful reproduction of one run from bundle" — demonstrated on
  real, previously-existing data, not a run created specifically to
  pass the demo.
- **Deviations, stated plainly:** `run_manifest.json` has no
  `experiment_id`/`cell_id` (still no link from `EORL Run` back to
  `EORL Experiment` — a gap open since Milestone 2); `requirements_lock.txt`
  pins frappe/erpnext/eorl_lab commits and the Python version, not a
  full `pip freeze`; "resolved_prompts/" is folded into
  `resolved_agent_configs/` since prompts aren't templated with runtime
  substitution yet — the stored instructions *are* the resolved prompt;
  `reproduce_run` only works for Milestone-5-and-later runs, by design,
  not by oversight (see the dedicated test above). Counterfactual replay
  from a *changed* configuration or a *specific episode* (spec section
  19's richer branching, with lineage fields back to a source run) is
  not built — this milestone is strictly "reproduce the same run
  exactly," not "branch from here with a different architecture."

---

## Test coverage so far

33 tests, all green, spanning Milestones 1–8:
- `test_eorl_settings.py`, `test_eorl_agent_template.py` (M1)
- `test_eorl_run.py` (M2, incl. an authority-denial test)
- `test_eorl_multi_agent_routine.py` (M3, incl. a submit-rights-denial
  test)
- `test_eorl_memory_and_repeated_episodes.py` (M4, incl. a
  memory-causality test and a no-memory-profile test)
- `test_eorl_architectures_and_shock.py` (M5, incl. the paired-seed/shock
  acceptance test)
- `test_eorl_experiment_studio_apis.py` (M6: cell/run-count math,
  validation incl. the stale-link edge case, a full paired-seed pilot
  launch exercised through Trace Explorer/Compare Runs/Export's own APIs)
- `test_eorl_process_metrics_synthetic.py` (M7: every formula against
  hand-computed values on controlled fixtures)
- `test_eorl_process_metrics_integration.py` (M7: real orchestrator runs
  through the real metrics pipeline, asserting both the coherence
  discrimination and the variety vacuity)
- `test_eorl_reproducibility.py` (M8: full bundle contents file-by-file,
  real reproduction with scenario-hash and metric verification, and a
  refusal test for pre-Milestone-5 runs)

Run: `bench --site erpnext.localhost run-tests --app eorl_lab`

---

## What's explicitly NOT built yet (honest gap list)

- `EORL Scenario` DocType — the full distributional scenario generator
  (spec section 11: demand/lead-time/quality distributions, exception
  families) needs it. The current generator is a fixed case with
  deterministic quantity variation, not a configurable distribution.
- `EORL Experiment`'s design is one-factor/two-level only (see Milestone
  6 above) — a real N-factor factorial table isn't built.
- Agent Studio, Architecture Designer (graphical node-edge editor),
  Scenario Studio — agents and architectures are composed via plain
  DocType forms, not purpose-built composition UIs.
- Routine-variety, repertoire, and adaptation metrics have nothing to
  discriminate on with today's deterministic, non-branching policies
  (see Milestone 7 above) — the math is built and tested, the signal
  isn't there yet. Needs either a non-deterministic/LLM provider or a
  real exception/ground-truth-driven scenario generator.
- Counterfactual replay from a *changed* configuration or branching from
  a *specific episode* with lineage back to a source run (spec section
  19's richer scope, beyond Milestone 8's "reproduce the same run
  exactly") — not built.
- `EORL Run` still has no link to `EORL Experiment` — run manifests omit
  experiment_id/cell_id (open since Milestone 2).
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
- The five new Desk pages have not been exercised in an actual browser
  by me (see Milestone 6 note above) — API-level and JS-review
  verification only.

---

*Last updated: end of Milestone 8.*
