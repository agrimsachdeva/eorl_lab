# EORL Lab — Build Progress

This is the build log for the Executable Organizational Routine Laboratory
(`eorl_lab`): what was built, what was tested, and what was run against real
data. It tracks the original build order in `EORL_LAB_AGENT_BUILD_SPEC.md`
(section 26, "V1"), Milestones 1 to 8. Every deviation from the spec is
called out where it happens, following the spec's own instruction (section
31: "document the deviation and its scientific consequences rather than
silently changing the design").

The later work against the larger V2 specification (SOTA Milestones 1 to 10)
has its own gap analysis and delivery notes in `SOTA_ROADMAP.md`. This file
keeps a short digest of that work so the whole project can be read in one
place, but `SOTA_ROADMAP.md` is the detailed record for it.

Repo: https://github.com/agrimsachdeva/eorl_lab (private)
Installed on: `erpnext.localhost` site, alongside `erp_research`, on the
dev-mode bench at `~/frappe_docker/development/frappe-bench` on `agrim`
(Docker Compose stack: `mariadb`, `redis-cache`, `redis-queue`, `frappe`
containers — see `~/frappe_docker/.devcontainer/docker-compose.yml`).

**Status as of 2026-11-01:** V1 Milestones 1 to 8 and SOTA Milestones 1 to 10
are complete. 140 automated tests pass. 26 DocTypes, 15 Desk pages, 29
whitelisted API functions, 15 semantic ERP tools. The Milestone 1 to 8 text
below is the record as written on 2026-10-29 and has not been edited. What
changed afterwards is tracked in "V1 gap list: status today" near the end.

Since SOTA Milestone 10 there is a hosted demonstration site
(`eorl-demo.localhost`) and a pre-registered pilot with language-model actors:
16 runs, 96 episodes, Qwen3 27B for every actor. It is the first evidence from
model-driven runs and it bears on proposition P1 only. See "After SOTA 10:
hosted demo and language-model pilot". The Word submissions in
`~/eorl_docx_updated/` (v3 files) report the same results.

The submission-day build (same day) implemented the Stage 1 plan: a second
routine, routine templates, three actor engines, matched exogenous
outcomes, a path-invalidating shock, registered sequence views,
attribute-level coherence, repertoire v2, more executable constructs,
multiplicity correction, effect-size intervals, interpretation rules, the
reviewer pages and the release documents. See "Submission-day build". The
Word submissions predate it and do not describe it.

## Contents

- At a glance
- How to run things
- Milestone 0: environment, migration and repository setup
- Milestones 1 to 8 (the original V1 build)
- After Milestone 8: SOTA Milestones 1 to 10
- After SOTA 10: hosted demo and language-model pilot
- Submission-day build (2026-11-01)
- Commit timeline
- What exists now (inventory)
- Reference runs
- Test coverage
- Problems found and fixed along the way
- V1 gap list: status today
- Open items today

---

## At a glance

All eight V1 milestones were committed on 2026-10-29. Test counts are
cumulative and were computed from the test files at HEAD (the Milestone 7
and 8 totals, 30 and 33, match what this document reported at the time).

| Phase | Commit | Date | Tests | What it delivered |
|---|---|---|---|---|
| 0. Environment | a35e74e | 2026-10-26 to 10-29 | 0 | Bench moved from a Jetstream VM to agrim in Docker; empty `eorl_lab` app created |
| 1. Skeleton | 4466366 | 2026-10-29 | 2 | Roles, config DocTypes, lab page |
| 2. Vertical slice | 4841dc2 | 2026-10-29 | 4 | Deterministic agent, authority firewall, first ERP tools, event trace |
| 3. Multi-agent routine | da20eb0 | 2026-10-29 | 6 | Four actors, full procure-to-pay chain, handoffs |
| 4. Memory | 91f77ea | 2026-10-29 | 8 | Episodic memory, repeated episodes |
| 5. Architectures and shock | 3cc222a | 2026-10-29 | 11 | Specialist vs broad autonomy, demand shock, paired seeds |
| 6. Research front end | 60e45dd | 2026-10-29 | 14 | Experiment Studio, Run Monitor, Trace Explorer, Compare Runs, Reproducibility pages |
| 7. Process metrics | 93fbc5f | 2026-10-29 | 30 | Sequence, coherence, repertoire and recovery metrics |
| 8. Reproducibility | ffc18a4 | 2026-10-29 | 33 | 14-file bundle and verified run reproduction |
| SOTA 1 | cfeeb38 | 2026-10-29 | 46 | Ground truth drives outcomes, authority model, process grammar, communication policy |
| SOTA 2 | 3e1b00b | 2026-10-29 | 52 | Counterfactual branching |
| SOTA 3 | d32e9f7 | 2026-10-29 | 69 | Real model provider (Qwen3 via vLLM), semantic and procedural memory |
| SOTA 4 | 3386786 | 2026-10-29 | 84 | Construct Registry, N-factor experiments, ablation marking |
| SOTA 5 | c5d5adf | 2026-10-30 | 97 | Statistical inference engine and Scientific Cockpit |
| SOTA 6 | 1025851 | 2026-10-30 | 109 | TOST equivalence, mixed-effects model, table export |
| SOTA 7 | 16aa6dd | 2026-10-30 | 114 | Process Explorer, Network Explorer, Adaptation View |
| SOTA 8 | 164b891 | 2026-10-30 | 126 | Power planning, robustness diagnostics |
| SOTA 9 | 36f5b1e | 2026-10-30 | 135 | QAP network comparison, Kaplan-Meier survival analysis |
| SOTA 10 | cd984f1 | 2026-10-30 | 140 | Paired-branch inference UI, Theory Compiler |

The docs website (commit 9f2bd9e, 2026-10-29) and a documentation quality
pass (commit 9038eac, 2026-10-30) sit between and after these milestones;
see the commit timeline.

---

## How to run things

```bash
# start the containers (on the lab machine, host shell)
cd ~/frappe_docker
docker compose -f .devcontainer/docker-compose.yml up -d

# enter the dev container
docker exec -it devcontainer-frappe-1 bash
cd /workspace/development/frappe-bench
source env/bin/activate

# start the web server, workers and scheduler (detached, reachable on the tailnet)
FRAPPE_BIND_ADDR=0.0.0.0 nohup bench start > logs/bench_start.log 2>&1 &

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

# give a model profile its API key (SOTA Milestone 3). The profile's
# api_key_reference field holds the NAME of a site-config key, never the key.
bench --site erpnext.localhost set-config <api_key_reference> <key>

# rebuild the docs site locally (from the app repo root, inside the container)
python3 docs/gen_doctype_docs.py && mkdocs build --strict
```

Long commands should be detached when driven over SSH
(`docker exec -d ... > log 2>&1; echo DONE_EXIT_$? >> log`) and polled with
short separate calls. A single long-lived SSH call can be cut off.

Browse results in the Desk at `erpnext.localhost:8000/app/eorl-run`,
`/app/eorl-episode`, `/app/eorl-event`, `/app/eorl-memory-record`, or through
the 15 Studio pages:

- Milestones 1 and 6: `/app/eorl-lab`, `/app/eorl-experiment-studio`,
  `/app/eorl-run-monitor`, `/app/eorl-trace-explorer`, `/app/eorl-compare-runs`,
  `/app/eorl-reproducibility`
- SOTA Milestones 5 to 10: `/app/eorl-scientific-cockpit`,
  `/app/eorl-process-explorer`, `/app/eorl-network-explorer`,
  `/app/eorl-adaptation-view`, `/app/eorl-power-planner`,
  `/app/eorl-robustness-diagnostics`, `/app/eorl-survival-analysis`,
  `/app/eorl-paired-branch-inference`, `/app/eorl-theory-compiler`

---

## Milestone 0 — Environment, migration and repository setup

This was done before any `eorl_lab` code existed. It is recorded here because
every later milestone depends on how the environment was built, and because
two of the steps went wrong the first time.

**Starting point (2026-10-26).** A Frappe bench at `~/my-bench` on a Jetstream
VM, run with `bench start`. It served four sites from one process: one web
server on port 8000, one socketio process on port 3000, and Frappe routing
requests by `Host` header. The sites were `erpnext.localhost`,
`agentic.localhost`, `auto.localhost` and `conversational.localhost`. Each had
its own MariaDB database and its own database user, which was checked directly
(the `erpnext.localhost` database user could see only its own database). They
shared one MariaDB server. One custom app, `erp_research`, ran on all of
them. Frappe 14 on Python 3.10.12.

*(Since 2026-11-01 this machine is `enterpriseailab` on the tailnet, MagicDNS
`enterpriseailab.taile74753.ts.net`. Its OS hostname and Linux account are still
`agrim`. The text below is the record as written and uses the old name.)*

**Goal.** Move this to the researcher's own machine, `agrim`, reachable over
Tailscale, and keep the Jetstream workflow: edit code on disk, live reload,
git history intact.

**What was done (2026-10-28 to 10-29).**

1. Tailscale was installed on the Jetstream VM and joined to the tailnet.
   Tailscale SSH was enabled on agrim with `sudo tailscale up --ssh`, and
   connections use the `agrim` account (`tailscale ssh agrim@agrim`).
2. agrim was inspected. It had plenty of disk (873 GB free), Python and git,
   but no Node, MariaDB or Redis. Its default Python was 3.12, which Frappe 14
   does not support (it needs 3.10 or 3.11). `sudo` on agrim needs a password,
   which cannot be given to a non-interactive session.
3. Docker was chosen over a bare-metal install, so Frappe's dependencies would
   not collide with the host's Python or leave MariaDB and Redis running as
   system services. The researcher ran the privileged install block (Docker
   Engine, compose plugin, docker group) on agrim themself.
4. On Jetstream, all four sites were backed up with files (`bench backup
   --with-files`) together with the `erp_research` app, both
   `common_site_config.json` and each `site_config.json`, and a version
   manifest. The bundle was 9.3 MB.
5. **First attempt, abandoned.** `frappe_docker`'s production "layered" image
   was built (it built, at about 2 GB, and was never put into use). It bakes
   app code into the image and strips `.git`, so there would be no live reload
   and no version control inside the container. That is the wrong shape for a
   research instrument still being written, so the build was dropped before
   use.
6. **Final setup.** `frappe_docker`'s dev-mode stack. The whole
   `frappe-bench` directory is bind-mounted from agrim's disk
   (`~/frappe_docker/development/frappe-bench`), so apps keep their git
   history and can be edited from the host. Four containers:
   `devcontainer-frappe-1`, `devcontainer-mariadb-1`,
   `devcontainer-redis-cache-1`, `devcontainer-redis-queue-1`. All four are set
   to `restart: unless-stopped`. `bench start` itself is not managed by Docker
   and is started by hand inside the frappe container.
7. **Mistake 1: wrong Python.** `bench init` picked up Python 3.14, which broke
   Frappe 14's pinned `pypika` build. Fixed by installing Python 3.10.12 with
   pyenv, matching Jetstream.
8. **Mistake 2: Python lost on container recreation.** The pyenv install lived
   outside the bind-mounted `/workspace`, so recreating the container removed
   it. Fixed with a named Docker volume for the pyenv versions.
9. All four sites were restored from the bundle with `bench restore`, public
   and private files were extracted, the per-site fields that do not travel in
   a database dump (`ai_mode` and the API-key fields) were merged back into
   each site config, and `bench migrate` was run on every site.
10. `eorl_lab` was created with `bench new-app` and installed on
    `erpnext.localhost` only, next to `erp_research` (spec section 1: same
    site, no dependency on the legacy app). A local git repository was
    created, and later pushed to GitHub. The remote is named `upstream`.

**Access.** Tailnet only. Ports 8000 to 8005 and 9000 to 9005 are published on
agrim's tailnet address, not on a public interface. To open a site from
another device on the tailnet, add a hosts-file entry that maps the
`*.localhost` names to agrim's tailnet address, then browse to
`http://erpnext.localhost:8000`.

**Public access was considered and not set up.** `bench start` runs Werkzeug's
interactive debugger, and there is no setting to turn it off, so putting the
dev server on the public internet would let anyone who triggers an unhandled
error get a Python console. The proposed fix was a second, hardened
gunicorn and nginx front end over the same site files, exposed with Tailscale
Funnel. As of 2026-11-01 `tailscale funnel status` on agrim reports no serve
configuration, so nothing is published.

**Versions on agrim, 2026-11-01.**

| Component | Version |
|---|---|
| Frappe | 14.101.1 |
| ERPNext | 14.92.14 |
| Python | 3.10.12 |
| scipy | 1.15.3 |
| numpy | 2.2.6 |
| pandas | 2.3.3 |
| statsmodels | 0.15.0 |
| lifelines | 0.30.0 |
| Apps on the bench | frappe, erpnext, erp_research 0.0.1, eorl_lab 0.0.1 |

`scipy`, `numpy`, `statsmodels`, `pandas` and `lifelines` are declared in the
app's `pyproject.toml`. Frappe and ERPNext are managed by bench.

**Working rules that came out of this setup.**

- Git commits and pushes are made from agrim's host shell, not inside the
  container.
- Tailscale SSH asks for a fresh browser approval from time to time. Nothing
  in the session can approve it; the researcher has to open the link.
- API keys are never stored in a DocType field or committed. A model profile
  stores the name of a site-config key (`api_key_reference`), and the provider
  reads the value from `frappe.conf` at run time.
- Statistics use existing packages (scipy, statsmodels, lifelines) instead of
  hand-written implementations. This was a standing instruction from the
  researcher during SOTA Milestone 5 and has been followed since.

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

## After Milestone 8: SOTA Milestones 1 to 10

After Milestone 8, a second specification arrived
(`docs/specs/EORL_SOTA_DEVELOPER_BUILD_SPEC_V2_ANALYTICS.md`, "V2"). It is
much larger than V1: formal authority, five memory types, a communication
graph, task allocation, a process grammar, a construct registry,
counterfactual branching, and a statistics workbench with no V1 counterpart.
`SOTA_ROADMAP.md` holds the gap analysis against V2 and a full delivery note
for each milestone below, including the deviations. This is the short version.

| SOTA milestone | Commit | What shipped | Verified on |
|---|---|---|---|
| 1. Structural gaps | cfeeb38 | Ground truth now drives outcomes (quality inspection, price). Authority model with hard constraints that block and soft rules that only log. Process Grammar, Communication Policy graph with an agent-chosen `message_agent` tool, Task Assignment records. | RUN-00012, 30 real episodes, 2 quality exceptions handled end to end: 2 unique sequences, sequence entropy 0.353, modal-path share 0.933. Before this, variety was exactly 0 on every run. |
| 2. Branching | 3e1b00b | Counterfactual branching. A child run shares its parent's episodes up to the branch point by reference, clones actor memory, continues the same scenario stream, and records lineage in `EORL Branch`. Also fixed a fragile ERPNext rate-fallback bug. | RUN-00072 branched at episode 2 into RUN-00073 and RUN-00074. Both children returned byte-identical episode 1 and 2 records and diverged from episode 3. |
| 3. Real model provider and memory | d32e9f7 | OpenAI-compatible provider wired to a self-hosted Qwen3 model served by vLLM. Provider chosen per actor from its own model profile. Semantic and procedural memory. A `finish_turn` tool so a model can end its turn. Three bugs fixed on the way: ERP pricing, uncaught provider failures, reasoning-budget starvation. | RUN-00083: a model completed a full procure-to-pay episode on its own, 11 tool calls, real ERP documents. One episode, not a study. |
| 4. Constructs and factorial design | 3386786 | Construct Registry with 8 seeded constructs, 2 of which have executable measurement functions. `EORL Experiment Factor` turns experiments into N-factor designs, backward compatible with the old two-architecture form. Ablation marking on runs. | A real 2x2 design (coordination structure x regime shift) produced 4 runs with paired seeds. |
| Docs website | 9f2bd9e | MkDocs Material site with a researcher guide, an API reference generated from docstrings and a DocType reference generated from each DocType's JSON. GitHub Actions deploys it to GitHub Pages on every push to main. | Site builds with `mkdocs build --strict`. |
| 5. Statistics engine | c5d5adf | scipy-backed Welch, permutation and paired tests, Hedges' g. `EORL Analysis Plan` with an enforced independence guardrail that refuses episode-level between-condition comparisons. `EORL Analysis Result` stores provenance linked to traces. Scientific Cockpit page. | Specialist handoff vs broad autonomy on actor continuity, 5 runs each: 0.713 vs 1.000, Welch p = 6.2e-8, permutation p = 0.0079. This validates the measurement chain, because scripted actors follow their architecture by construction. |
| 6. Equivalence and mixed models | 1025851 | TOST equivalence testing, a mixed-effects model (statsmodels `MixedLM`, run as a random-effect cluster) so episode-level analysis is allowed instead of refused, publication table export in two formats. | Two broad-autonomy architectures, 5 runs each: Welch gave nan and the permutation test p = 1.0 (inconclusive), while TOST established equivalence (p = 0.0). |
| 7. Process, network and adaptation views | 16aa6dd | Process Explorer (directly-follows graph and episode swimlane), Network Explorer (agent-message network), Adaptation View (event study around a regime shift). All built on data that already existed. | A 30-episode specialist run with a regime shift at episode 20: the graph split one node 50/50 into its two real successors, and the network showed the 4-stage handoff chain. |
| 8. Power and robustness | 164b891 | Power and sample-size planning by Monte Carlo simulation of the exact Welch test the engine runs. Robustness diagnostics: leave-one-run-out sensitivity and cumulative effect-estimate stability. | Broad autonomy vs specialist handoff, 6 runs each: the effect held at 0.2895 from n = 2 and the largest leave-one-out shift was floating-point noise. |
| 9. Network comparison and survival | 36f5b1e | QAP and MRQAP network comparison (significance from actor-label permutation, not treating edges as independent). Kaplan-Meier time-to-recovery with right-censoring for runs that never recover, via lifelines. | QAP on two real runs gave p = 0.044, the smallest the 4-actor permutation space allows (1/24). Kaplan-Meier on 5 real shocked runs: all recovered immediately, because the demand shock never lowers success. |
| 10. Paired branches and theory compiler | cd984f1 | Paired-Branch Inference page (groups branches by shared source episode, matching the analysis engine's own paired check). Linked episode-level navigation between Process Explorer, Adaptation View and Trace Explorer. Theory Compiler wizard that scaffolds an Experiment and an Analysis Plan from 8 researcher inputs. | Two real sibling branches grouped correctly and kept apart from an unrelated branch. `compile_theory` produced a draft Experiment and Analysis Plan with the outcome metric resolved from the construct's measurement function. |
| Docs quality pass | 9038eac | Rewrote the researcher guide (`docs/index.md` and `docs/guide/*.md`) for tone and accuracy and cut repetitive phrasing. | 13 files changed. |

Two limits apply to the whole SOTA block. Cross-filtering is linked
navigation, not live in-place re-rendering of one panel from another. The
Theory Compiler is a structured wizard, not an autonomous generator.

---

## After SOTA 10: hosted demo and language-model pilot

Written 2026-11-01 while preparing the Stage 1 submission to the Organization
Science special issue. Until this point the only evidence was validation of
the instrument with scripted actors, which says nothing about the theory. The
work below adds a clean hosted site for reviewers and the first language-model
comparison. None of it is committed to git yet (see "Open items today").

### Hosted demonstration site

- A second Frappe site, `eorl-demo.localhost`, on port 8002 of the same bench.
  It holds synthetic data only: a fictitious company, two milk suppliers and
  one stock item (MILK-001). It does not contain the participant data on
  `erpnext.localhost`, which stays on port 8001 and is not exposed.
- Reachable on the tailnet only when first built. Since 2026-11-01 it is public
  through Tailscale Funnel at `https://enterpriseailab.taile74753.ts.net`, which
  proxies to port 8002 only, and its `host_name` is set to that address (see
  RUNNING_AND_SHARING.md section 7). A supervisor script outside the repository
  (`~/eorl_live/eorl_live_ctl.sh start|stop|status`) runs both servers.
  Credentials are in `~/eorl_live/credentials.env`, mode 600.
- A read-only reviewer account holds the EORL Viewer role. It can read every
  EORL record and run the analysis pages, but cannot open Experiment Studio,
  launch runs or change configuration.
- The model key is held in site configuration under the name the Model
  Profile gives (`qwen_api_key`), never in a DocType field, and is not
  committed.
- The scripts that built the site and ran the pilot are in `pilot/` (see
  `pilot/README.md`): `demo_setup.py`, `demo_seed.py`, `pilot_setup.py`,
  `pilot_prereg.py`, `pilot_smoke.py`, `pilot_run.py`, `pilot_analyze.py`.

Run numbers on the demo site, which differ from the dev site above:

| Runs | What they are |
|---|---|
| RUN-00001 to RUN-00010 | Scripted runs, five specialist and five broad, behind the positive control |
| RUN-00011 | 30 scripted episodes with ground-truth-driven exceptions (3 quality exceptions, entropy 0.469, modal-path share 0.900) |
| RUN-00012 | Branch child of RUN-00001 that switches to broad autonomy at episode 2 |
| RUN-00013 to RUN-00016 | Smoke checks of the model engine before the pilot. RUN-00013 failed at the output-token limit. None is analyzed. |
| RUN-00017 to RUN-00032 | The 16 pilot runs |
| RUN-00033 | Second branch child of RUN-00001, continuing specialist handoff, created after the pilot |

### The pilot

- **Design.** Specialist Handoff (four role-bounded actors, each with the
  tools of one stage) against Broad Autonomy (one actor with all thirteen
  tools). The same Qwen3 27B profile for every actor (temperature 0.6,
  thinking on), no memory, no `message_agent` tool, the same instruction
  preface. Seeds 7100 to 7107, each run under both architectures with the
  order alternating by repetition, six episodes per run, no regime shift. The
  16 runs are the independent units.
- **Registration.** The Experiment, its hypotheses, an interpretation rule and
  three Analysis Plans were stored before the first run was created (the
  timestamps are about nine seconds apart). The record is internal to the
  site. It is not in an external registry.
- **Primary measures.** Modal-path share and sequence entropy per run, from
  tool-result events (`finish_turn` is excluded). Equivalence bounds of
  ±0.17 and ±0.65 bits, each the change produced when one of six episodes
  leaves the modal path. Actor continuity is a manipulation check.
- **Tests.** Welch, permutation (10,000 resamples), Hedges' g and TOST at
  run level, unpaired, because the quality outcome of a receipt is drawn from
  the receipt's name and so does not match across arms.
- **Cost.** A six-episode run took 596 to 685 seconds under Specialist
  Handoff and 390 to 497 under Broad Autonomy, about 2.4 hours of model time
  for the 16 runs. 54 runs of that length would take about 8 hours.

| Measure | Specialist | Broad | Difference [95% CI] | Welch p / permutation p | Equivalence (TOST) |
|---|---|---|---|---|---|
| Modal-path share | 0.54 (SD 0.17) | 0.85 (0.19) | -0.31 [-0.51, -0.12] | .004 / .015 | Not established, p = .932 |
| Sequence entropy (bits) | 1.26 (0.47) | 0.40 (0.45) | 0.86 [0.37, 1.35] | .002 / .002 | Not established, p = .816 |
| Actor continuity (check) | 0.75 (0.004) | 1.00 (0.000) | -0.25 | < .001 / < .001 | Not applicable |

Hedges' g was -1.64 for modal-path share and 1.78 for entropy (point
estimates, no interval computed). All 96 episodes completed the purchase
order, receipt, invoice and payment, and no tool call was denied. Every
episode chose the same supplier, so the second supplier was never used.
Episodes held 15.6 tool calls (SD 0.6) under Specialist Handoff and 11.1 (0.4)
under Broad Autonomy, counting `finish_turn`. A quality exception arose in 3
of 48 specialist and 7 of 48 broad episodes (Fisher p = .32), and each was
escalated.

**How to read it.** As registered, hypothesis H1 holds: Broad Autonomy had a
higher modal-path share and lower entropy, and equivalence was not
established. That counts against the rival constraint-dominance account's
prediction of no difference. The recorded interpretation rule covers only
equivalence on both measures and a failure of equivalence without a
significant difference, so it has no case for this outcome.

It is weak evidence for P1, because the difference comes from optional
read-only calls. In 24 of 48 specialist episodes the accounts-payable actor
called `get_receipt_status` before invoicing, and in 3 of 48 the warehouse
actor read the purchase order a second time. No broad episode did either,
though the broad actor held the same tools. The registered measures count
those calls, so an optional check split many specialist runs between two
paths. A post hoc check (designed after seeing the data, not registered)
removed the three read-only tools from every sequence. Modal-path share was
then 0.94 under Specialist Handoff and 0.85 under Broad Autonomy (Welch p =
.28, permutation p = .44), and entropy was 0.24 and 0.40 bits (p = .44 and
.52). Both differences changed sign and neither is reliable.

The accounts-payable instruction also does not mention receipt status while
the broad instruction lists every step, so the pilot cannot separate role
boundaries from instruction wording or from the number of actors. The two
architectures differ in actors, tool breadth and handoffs, so the pilot
compares bundles of design features and does not isolate autonomy.

**What it does not cover.** P2 (memory) is untested because no memory
conditions were run. P3 (adaptation) is untested because there is no
supplier-quality shock. There is one model, one routine and one scenario.
These need the Stage 2 designs: a broad variant with matched tools, a shock
that invalidates previously successful paths, memory conditions, more runs
(27 per architecture for an effect of 0.8), non-LLM baselines and a second
model family.

### Other work in the same stretch

- The full test suite was re-run on 2026-11-01 on `erpnext.localhost`:
  `Ran 140 tests in 453.059s ... OK`.
- New figures for the appendix: a branch diagram, a development-progress
  figure, a screenshots composite built from the hosted site (Scientific
  Cockpit and a pilot run in Process Explorer), and a pilot results figure
  with registered and post hoc panels.
- Word submissions v3 (`~/eorl_docx_updated/`): the proposal has a pilot
  paragraph, and the Technical Appendix has Section 7.4 (the pilot) and
  Section 11 (prototype access and technical specification, with 11.4 on
  reproducing the pilot). Run identifiers in both match the hosted site.
  `CHANGELOG.md` in that folder lists the changes and what needs author
  confirmation.

---

## Submission-day build (2026-11-01)

Built from `EORL_SUBMISSION_DAY_IMPLEMENTATION_PLAN.md` for the Stage 1
submission. The organizing rule was the plan's: EORL is the contribution,
and agentic routinization is its first demonstration. Plan section numbers
are given in brackets.

### What was built

| Area | What exists now |
|---|---|
| Platform vs demonstration [1.1, 13, 29] | `experiment_type` (infrastructure_validation, theory_demonstration, empirical_study) and `demonstration` on EORL Experiment. The Lab home page lists building blocks and demonstrations separately. Runs carry `experiment` and `cell_id`, closing the long-open gap. |
| Second routine [2.1, 15] | `EORL Routine Template` DocType (stage order, roles, handoff keys, per-stage tools, scenario generator, terminal conditions). The orchestrator no longer names a routine. Procure-to-Pay and Order-to-Cash ship as templates with process grammars. Order-to-cash has its own scenario generator, eleven ERP tools (sales order, delivery note, sales invoice, customer payment) and a non-stock sales item, so it leaves MILK-001 untouched. |
| Terminal conditions | An episode counts as complete only if the routine's end state holds. Previously a broad actor that called `finish_turn` early would have been recorded as a success. |
| Constructs [3.1] | `status` on EORL Construct. Three existing entries gained measurement functions (Centralization, Specialization, Information asymmetry) and four executable entries were added (Sequential variety, Routine concentration, Attribute-level path coherence, Communication centralization): 9 of 12 entries are executable, 3 remain conceptual. Functions in `eorl_lab.analysis.constructs`. Citations given only where certain; Information asymmetry says "to be completed by the author". |
| Attribute-level coherence [4.1] | `path_coherence_v1` over eight attributes and a composite (`eorl_lab.analysis.attribute_coherence`). The docstring and the registry entry say the formula is an EORL operationalization not verified against the cited paper's estimator. |
| Path-invalidating shock [5.1] | Regime shifts can declare `pre_shock_latent_ground_truth` and `post_shock_latent_ground_truth`. The demonstration reversal: Bloomington Dairy quality 0.95 to 0.58, Indiana Foods 0.78 to 0.91 at episode 7. `get_supplier_options` now returns the scenario's candidate suppliers, so latent parameters apply on any site (on `erpnext.localhost` it had been returning whatever suppliers ERPNext listed). |
| Adaptive repertoire [6.1] | Repertoire v2: observed, viable (completed, no hard violation, utility at least 0.9) and activated-after-shock paths kept apart, with utilization, retention, reuse, novelty, extinction and activation latency. Shock adaptation: pre-shock dominant path and supplier mix, episodes to first adaptive and to stable new path (both require viability), performance deficit. Outcome utility v1 = 1 minus the share of units rejected. |
| Memory manipulation [7.1] | SD-B below. `configuration_difference` confirms the memory and no-memory branches differ only in four `memory_profile_config` fields. |
| Matched-tools condition [8.1] | `stage_gated_tools` on EORL Architecture: one actor, offered and authorized only the current stage's tools. The gate is enforced outside the model (`STAGE_GATED` denials). |
| Non-LLM baseline [9.1] | `actor_engine` chosen independently of architecture: `scripted_deterministic`, `bounded_rational` (new, `eorl_lab.providers.bounded_rational`), `llm`. |
| Multiplicity [10.1] | `adjustment_method` with `multiple_testing_family`; Holm, Benjamini-Hochberg, Bonferroni via statsmodels; adjusted p written to each family member's primary result. |
| Effect-size CI [11.1] | Seeded percentile bootstrap for Hedges' g (paired and unpaired). Degenerate resamples are dropped and the kept share reported; the interval is undefined below 90%. |
| Power planning [12.1] | `random_seed`; seeded power tables for independent and paired designs with Monte Carlo standard errors; the page no longer hard-codes 0.8. Same seed, same table (tested). |
| Reviewer page, matrix [13, 15] | `/app/eorl-reviewer` (eleven steps, each resolved to a real record from `EORL Settings.reviewer_walkthrough_json`) and `/app/eorl-evaluation-matrix` (eight criteria, live counts). |
| Read-only reviewer [14] | `compare_groups` and `compute_run_metrics` compute but do not persist without create permission. Role checks on the twelve whitelisted read functions that lacked them. Model Profile `base_url` and `api_key_reference` moved to permission level 1, which the Viewer role cannot read; model events record the profile name, not the URL. |
| Release [16, 17] | README rewritten; QUICKSTART, REVIEWER_GUIDE, ARCHITECTURE, REPRODUCIBILITY, LIMITATIONS, LICENSE, CHANGELOG, CITATION.cff; `scripts/generate_artifact_manifest.py` writes `artifact_manifest.json`. |
| Export [18] | `public/js/eorl_export.js`: CSV with metadata header lines, JSON, copy-specification, on Process Explorer, Adaptation View, Scientific Cockpit, Power Planner and Evaluation Matrix. Metadata carries run IDs, plan, scope, metric version and timestamp. PNG/SVG export is not built. |
| Sequence views [19] | Action taxonomy (sense, decide, execute, verify, approve, communicate, control) and `sequence_scope` on the Analysis Plan: all_actions, consequential_actions, write_actions, actor_function_actions. Scoped metrics are stored as `metric@scope`. |
| Interpretation rules [20] | Structured rule fields on the Analysis Plan and `interpretation_combination` (AND, OR, weighted, separate) on the Experiment. A test enumerates every combination of significance, direction and equivalence and checks each maps to one of four labels. |
| Matched outcomes [21] | Outcome model `matched_v2`: the inspection draw is keyed on case and supplier, not on the receipt name. Set after hashing, so existing case hashes are unchanged. Old runs reproduce with `receipt_keyed_v1`. |
| Exogenous/endogenous [22] | Every `environment_observed` event carries `exogenous_state` and the list of endogenous sources. |
| Telemetry [23] | Per model call: tokens, latency, retries, profile. Per run: model calls, input/output/total tokens, retries, wallclock. `estimate_experiment_cost` and its display in Experiment Studio. |
| Queue [24] | `eorl_lab.api.queue` (enqueue run, enqueue experiment, cancel, list). Cancellation is checked between episodes through the cache. Needs a `bench worker --queue long`, which the live supervisor does not start. |
| Failure taxonomy [25] | `failure_type`, `retryable`, `retry_count` on EORL Run; `failure_type` and `utility` on EORL Episode. |
| UI fixes | Cockpit shows p below 0.0001 in scientific notation, g with its interval, adjusted p and the interpretation label. Trace Explorer marks success or failure only on events that carry an outcome. |

Not built from the plan: a second model family [26], Sankey, motifs and
clustering [27, Tier 5], PNG/SVG figure export [18].

### Problems found and fixed during the build

| Problem | Fix |
|---|---|
| Frappe 14 Float columns are NOT NULL, so every undefined value had been stored as 0: a NaN p-value from a zero-variance comparison, `episodes_to_recover_90pct` for a run that never recovered, information asymmetry for a one-actor organization. This predates today. | `EORL Metric.value_undefined` and `EORL Analysis Result.undefined_fields` flag them; `_run_level_metric` refuses an undefined value; p-values are read from `diagnostics_json`, which holds null. Rows written before the fix cannot be told apart from true zeros; recomputing a run's metrics writes flagged rows, and the newest row is the one read. |
| The first version of the effect-size bootstrap scored degenerate resamples as g = 0, which pinned interval bounds at exactly 0. | Degenerate resamples dropped and counted (above). |
| `evaluate_experiment_interpretation` read the 0.0 stored in `adjusted_p_value` for plans with no family as p = 0, and looked for the TOST by timestamp, which missed it. | Adjusted p is used only when the result has a family; the TOST is matched by run IDs. Regression test added. |
| `episodes_to_first_adaptive_path` counted a quality-exception path (different but worse) as adaptation. | Adaptive and stable new paths must be viable. |
| While switching the recovery metrics to utility, `success_rate` was briefly computed from utility too; the full suite caught it. On the demo site this wrote wrong `success_rate` rows for the SD runs only, and no stored plan reads that metric. | Fixed and covered by a test; the SD runs' metrics were recomputed, and the newest row is the one read. |
| A metric row written for a run that was later rolled back could be read for a new run that received the same name. | Metric lookups accept only rows created after the run itself. |
| A cancel flag left in Redis by a rolled-back test run cancelled the next run that reused its name. | A newly created run clears any flag under its name. |
| Frappe 14 `enqueue` has no `job_id`/`deduplicate` arguments; they would have been passed to the job function. | Uses `job_name`. |
| A Server Script on `User` on `erpnext.localhost` (from the erp_research data) fails with `__import__ not found`, so a test cannot create a user there. | The read-only test patches the permission check and separately asserts from DocPerm that EORL Viewer has no write, create, delete, submit or cancel on any EORL DocType. |

Changed definitions, versioned: the recovery metrics now use
utility and carry `v2+utility`; every other existing metric keeps `v1`.
Repertoire v2 metrics carry `v2+viability:v2`; scoped metrics add
`+scope:<scope>+taxonomy:v1`; construct metrics `constructs:v1`.

### Demonstration runs on the hosted site

All on `eorl-demo.localhost`. Experiments, plans and interpretation rules
were stored by `eorl_lab.demonstrations.submission_day.setup()` before any
run. Five seeds, 8101 to 8105. Labeled throughout as demonstration or
validation, not tests of the theory.

| Design | Runs | What it shows |
|---|---|---|
| SD-A, infrastructure_validation, scripted | RUN-00034 to RUN-00043: 5 specialist, 5 broad, 6 episodes | Matched outcomes: in all 30 episode pairs, same supplier and identical inspection result. Actor continuity 0.709 vs 1.000 (manipulation check, Welch p = 2.0e-7). Consequential-action entropy identical across arms (0.460 vs 0.460, TOST equivalence established). |
| SD-D, infrastructure_validation, scripted | RUN-00044 to RUN-00047: order-to-cash, 2 specialist, 2 broad, 3 episodes | Second routine runs end to end through the same orchestrator. All 12 episodes completed. |
| SD-B, theory_demonstration, bounded-rational | Parents RUN-00048, 51, 54, 57, 60 (episodes 1 to 6, pre-shock, with memory); each branched at episode 6 into a memory child (RUN-00049, 52, 55, 58, 61) and a no-memory child (RUN-00050, 53, 56, 59, 62) for episodes 7 to 12 after the reversal | Post-shock mean utility 0.888 (memory) vs 0.874 (no memory), paired t p = .37, Holm-adjusted .75; the g interval is undefined because most within-pair differences are exactly 0. Registered label: inconclusive on both outcomes. In rep 1 the memory child switched to Indiana Foods and stayed (IBIIII); its no-memory sibling went back to Bloomington (IBBBBB). In the other reps the two siblings behaved identically. |
| SD-C, theory_demonstration, bounded-rational | RUN-00063 to RUN-00077: specialist, broad and broad with matched tools, 5 reps each, 12 episodes, reversal at 7 | Post-shock mean utility 0.874 (specialist) vs 0.888 (broad), Welch p = .55, Holm-adjusted 1.0; performance deficit likewise. Broad and matched-tools broad were identical in every run (the non-semantic engine follows stage order either way), mean difference 0, TOST not established with n = 5. All three registered labels: inconclusive. Only rep 1 shows the mechanism: an exploration draw sent every arm to Indiana Foods at episode 7; after the next Bloomington failure the broad actor, which sees inspections, switched for good (BBBBBBIBIIII), while the specialist purchasing actor, which never sees them, returned to Bloomington. |

Reading. The instrument produced and measured everything it was meant to:
matched exogenous outcomes, a shock that changes which supplier is better,
branch-matched memory conditions confirmed by manifest, repertoire and
adaptation measures, family-adjusted tests and registered labels. The
designs are too small to show an effect: with a three-record memory window
and a 0.58 post-shock quality, two failures inside the window, which the
learner needs before it switches, were rare in six post-shock episodes.
The engine and the registered plans were not changed after seeing this.

Record-keeping notes. `analyze()` was run twice. The first batch of SD
results (08:23 UTC) used the first bootstrap implementation, whose
intervals were biased toward 0; the second batch is current, and family
adjustment and the interpretation endpoint read the latest batch. Both are
kept. `set_reviewer_walkthrough()` points the reviewer page at the Qwen3
pilot (its specialist architecture, RUN-00017, plan "Pilot P1: modal path
share" and its first Welch result), RUN-00001's branches, RUN-00064 for adaptation and RUN-00044 for
the second routine. The backfill patch `v2_backfill_run_provenance` set
`actor_engine` and `routine_template` on the 33 runs that predate them,
from the model profiles named in their own snapshots.

### Change log by file

Every file the build added or changed. Paths are relative to the
repository root; `eorl_lab/` below is the Python package. 65 tracked files
changed (4,411 lines added, 665 removed) and 35 paths were added. Nothing
was committed during the build.

#### New Python modules

| File | Contents |
|---|---|
| `eorl_lab/analysis/taxonomy.py` | `TOOL_CATEGORY` (sense, decide, execute, verify, approve, communicate, control for all 26 tools), `TOOL_OBJECT_TYPE`, `TOOL_DECISION_DOMAIN`, `SEQUENCE_SCOPES` (all_actions, consequential_actions, write_actions, actor_function_actions), `DECISION_ATTRIBUTE_BY_TOOL` (supplier for `create_purchase_order`, customer for `create_sales_order`), `in_scope()`, `scope_metric_name()` (`metric@scope`), `TAXONOMY_VERSION = "v1"`. |
| `eorl_lab/analysis/attribute_coherence.py` | `attribute_coherence(events, scope)`: share of consecutive action pairs within an episode sharing each of eight attributes (actor, role, stage, object_type, counterparty, exception_state, tool_family, decision_domain), averaged over episodes, plus an unweighted composite. `PATH_COHERENCE_VERSION = "path_coherence_v1"`. The docstring states the formula is an EORL adaptation. |
| `eorl_lab/analysis/adaptation.py` | `shock_adaptation()`: pre-shock dominant path and its share, pre/post supplier distribution, post-shock share on the old path, episodes to first adaptive path and to stable new path (both require viability; stable window 3), pre/post mean utility, performance deficit. |
| `eorl_lab/analysis/constructs.py` | `observed_state_variables`, `information_asymmetry` (1 minus mean pairwise Jaccard overlap), `authority_centralization` (normalized HHI per right over decision, approval, assignment), `tool_breadth_specialization`, `task_domain_entropy`, `communication_centralization` (Freeman degree). `CONSTRUCT_MEASURES_VERSION = "v1"`. |
| `eorl_lab/analysis/interpretation.py` | `classify()` maps significance, direction and TOST verdict to consistent, inconsistent, inconclusive or not_evaluated through five rule fields (`DEFAULT_RULES`); `combine()` under AND, OR, weighted or separate. |
| `eorl_lab/routines.py` | `BUILTIN_ROUTINES` for Procure-to-Pay and Order-to-Cash (stages with role, slot, handoff keys, tools, completion key; scenario generator; exogenous-state function; terminal conditions; outcome keys; broad slot and role; memory domain), `BUILTIN_GRAMMARS`, `resolve_routine()`, `required_tools()`, `seed_routine_templates()` (idempotent; creates grammars with stages and transitions, then templates). |
| `eorl_lab/scenarios/order_to_cash.py` | `generate_case()` (customer alternates by seed and episode, qty 20 to 35, selling rate 1.25, latent `payment_reliability` not yet read by any tool), `exogenous_state()`, `ensure_master_data()` (creates customers "EORL Demo Customer" and "EORL Second Customer" and the non-stock sales item `EORL-O2C-TUB`). |
| `eorl_lab/erp/selling.py` | Eleven order-to-cash tools: `get_customer_order`, `create_sales_order`, `get_sales_order`, `submit_sales_order`, `create_delivery_note`, `submit_delivery_note`, `get_delivery_status`, `create_sales_invoice`, `submit_sales_invoice`, `create_customer_payment`, `submit_customer_payment`. Documents are made with ERPNext's own mappers. |
| `eorl_lab/providers/bounded_rational.py` | `BoundedRationalProvider(DeterministicProvider)`: supplier quality estimate (passes + 1) / (observations + 2) from the actor's recalled records that carry an inspection result, 0.5 for an unseen supplier, ties to the first listed; 10% exploration; optional checks taken with probability 0.5. All draws keyed on case id, seed and purpose, not on actor. `quality_evidence()`; `ENGINE_VERSION = "bounded_rational_v1"`. |
| `eorl_lab/api/queue.py` | `enqueue_run`, `enqueue_experiment`, `cancel_run`, `list_queue`. Creates the run row as "queued", commits, and enqueues `orchestrator.run_queued` on the `long` queue with a 6-hour timeout. Cancellation sets a cache key `eorl_cancel:<run>` for 7 days. |
| `eorl_lab/api/reviewer.py` | `get_reviewer_walkthrough` (eleven steps resolved from `EORL Settings.reviewer_walkthrough_json`, missing keys filled with the most recent matching record), `get_artifact_manifest`, `get_evaluation_matrix` (`EVALUATION_MATRIX`, eight criteria, live counts), `configuration_difference()` and `compare_run_configurations` (flattened field-by-field diff of two runs' frozen configuration, document names ignored, optional allowed prefixes). |
| `eorl_lab/demonstrations/__init__.py`, `eorl_lab/demonstrations/submission_day.py` | `setup()` (profiles, memory profiles, the reversal regime shift, SD and O2C policies, agents and architectures, experiments SD-A to SD-D with their Analysis Plans; labels the two existing demo-site experiments), `run_experiment(key)` (SD-B as five parents branched into memory and no-memory children), `analyze()`, `verify_matched_outcomes()`, `set_reviewer_walkthrough()`. |
| `eorl_lab/patches/v2_construct_registry_measures.py` | Updates Centralization, Specialization and Information asymmetry (measurement function, definition, citations, limits, status executable, version 2.0), Routine coherence (citation, 1.1), Adaptive repertoire (repertoire v2, 2.0); sets Formalization, Hierarchy and Transactive memory to conceptual; inserts Sequential variety, Routine concentration, Attribute-level path coherence and Communication centralization. |
| `eorl_lab/patches/v2_seed_routine_templates.py` | Calls `seed_routine_templates()` and, where the company exists, `ensure_master_data()`. |
| `eorl_lab/patches/v2_backfill_run_provenance.py` | Fills `actor_engine` and `routine_template` on runs that predate them, from the model profiles named in each run's frozen agent snapshot. |

#### New DocType and pages

| File | Contents |
|---|---|
| `eorl_lab/eorl_lab/doctype/eorl_routine_template/` (`.json`, `.py`, `__init__.py`) | DocType EORL Routine Template, named by `routine_name`: version, domain, description, process_grammar, required_tools, default_roles, `stage_sequence_json` (required), scenario_generator (required), exogenous_state_function, terminal_conditions, outcome_keys, broad_slot, broad_role, memory_domain, default_metrics. Viewer read-only. The controller validates each stage has role, slot, tools and completes_on and that the generator path resolves; `to_definition()` returns the plain dict the orchestrator uses. |
| `eorl_lab/eorl_lab/page/eorl_reviewer/` | Page `eorl-reviewer`, "Reviewer Walkthrough, approximate time 5 minutes": what EORL is, the demonstration label, whether the account is read-only, artifact commit and test count, eleven step cards with an Open button each. All four EORL roles. |
| `eorl_lab/eorl_lab/page/eorl_evaluation_matrix/` | Page `eorl-evaluation-matrix`: criterion, capability, evidence, verification path, limitation; export buttons. |
| `eorl_lab/public/js/eorl_export.js` | `eorl_lab.export.csv` (metadata as `# key: value` lines), `json`, `copy`, `buttons(page, getter)` adding Download CSV, Download JSON and Copy specification under an Export menu. Loaded through `app_include_js`. |

#### Changed Python modules

| File | Change |
|---|---|
| `eorl_lab/runtime/orchestrator.py` | Imports `routines`, `time`, `engine_type_of`. Adds `FAILURE_TYPES`, `RETRYABLE_FAILURE_TYPES`, `_classify_provider_failure`, `_classify_tool_failure`, `_cancel_requested`. `_run_actor_turn` gains `tool_gate`, returns a fourth value (failure type), filters offered tools by the gate and denies gated-out tools with `STAGE_GATED`, times each provider call, accumulates tokens, latency and retries into `ctx.telemetry`, logs them on `model_response` with the profile name, and marks denials expected or unexpected from `ctx.expected_denial_codes`. `_summarize_actor_action` appends `;quality:passed|failed` when the actor saw the inspection, with a generic `completed:` fallback. `_retrieve_memory` and `_write_memory` take a domain. `_SPECIALIST_SEQUENCE` replaced by the routine's stages; new `_episode_outcome` (terminal-condition check, utility, failure reason and type), `_stage_gate`. `_run_specialist_episode` and `_run_broad_autonomy_episode` take routine and engine override; broad takes `stage_gated`. Snapshots add `model_profile_config`, `memory_profile_config`, `tool_policy_config` (`_profile_config`, `_tool_policy_config`). `_run_episode_loop` takes routine, outcome model and stage gating; resolves the generator from the routine; writes `environmental_state_hash`, `utility`, `failure_type`; logs `exogenous_state` and `endogenous_state_sources`; honors cancellation between episodes; writes status "cancelled", failure type, retryable, model calls, tokens, retries and wallclock to the run. New `_regime_shift_payload`, `_scenario_snapshot`, `_code_commit`, `_configured_engine`, `run_queued`. `run_architecture` gains `actor_engine`, `outcome_model`, `experiment`, `cell_id`, `existing_run`, `expected_denial_codes`, records scenario snapshot, routine, engine and code commit, and clears a stale cancel flag on a new run. `branch_run` keeps the source run's outcome model, engine and experiment. |
| `eorl_lab/runtime/authority.py` | Order-to-cash reads added to `READ_TOOLS`, writes to `WRITE_TOOLS`. |
| `eorl_lab/scenarios/procurement.py` | `copy.deepcopy` of the base case (the shallow copy would have let overrides mutate it). `OUTCOME_MODELS`, `DEFAULT_OUTCOME_MODEL = "matched_v2"`. `generate_case` gains `outcome_model`, applies `pre_shock_latent_ground_truth` / `post_shock_latent_ground_truth`, applies `qty_multiplier` only after the trigger as before, and sets `outcome_model` after hashing. New `_apply_ground_truth_override`, `exogenous_state`. |
| `eorl_lab/erp/stock.py` | `_quality_draw_key`: matched model keys on case id, seed, episode and supplier; legacy model keeps the receipt-name key. |
| `eorl_lab/erp/buying.py` | `get_supplier_options` takes `_case` and returns the scenario's candidate suppliers that exist in ERPNext; falls back to the old lookup without a case. |
| `eorl_lab/erp/registry.py` | Registers the eleven order-to-cash tools. |
| `eorl_lab/analysis/paths.py` | `PROCESS_STAGE_BY_TOOL` adds `finish_turn: CONTROL` and the order-to-cash stages. `CanonicalActionEvent` adds `category`, `attributes`, `decision_value`. `_payload()`; `extract_canonical_events` builds attribute vectors with supplier and exception state carried forward within an episode; `scoped_events()`; `process_path(..., scope)` with `_token()` (annotation outside all_actions; ROLE:action for actor_function_actions). |
| `eorl_lab/analysis/repertoire.py` | Appended `VIABILITY_CRITERION_V2`, `DEFAULT_UTILITY_THRESHOLD = 0.9`, `episode_utility`, `is_viable_v2`, `adaptive_repertoire`. Existing functions unchanged. |
| `eorl_lab/analysis/stats.py` | Appended `DEFAULT_BOOTSTRAP_SEED = 20261101`, `hedges_g_bootstrap_ci` (seeded percentile bootstrap, degenerate resamples dropped, `valid_share`, undefined below 0.9), `ADJUSTMENT_METHODS`, `adjust_p_values` (statsmodels `multipletests`), `simulate_paired_power`, `power_grid`. Existing functions unchanged. |
| `eorl_lab/api/metrics.py` | `METRIC_VERSION` stays `v1`; `RECOVERY_METRIC_VERSION = "v2+utility"` for the four recovery metrics; versions for repertoire v2, construct and scoped metrics; public `metric_version()`. `_episode_data` fetches `payload_json`. `compute_run_metrics`: persists only with create permission on EORL Metric; recovery metrics on utility, `success_rate` on the success flag; adds `mean_utility`, the four sequence metrics for each non-default scope, `path_coherence_v1` with per-attribute values for all and consequential scopes, repertoire v2, shock adaptation, five construct metrics. `_save_metric` sets `value_undefined`. New `_chosen_counterparty`, `_authority_configuration`. Role check on `compare_runs`. |
| `eorl_lab/api/analysis.py` | `READ_ROLES`, `_PRIMARY_TEST`, `_plan_metric_name` (scoped names), `_primary_test_name`, `_can_persist`. `_run_level_metric` reads the newest row created after the run and refuses undefined values. `_save_analysis_result` writes the g interval, sequence scope, family, primary flag, interpretation label, adjusted p and `undefined_fields`, and the per-metric definition version. `compare_groups`: role check; seeded permutation tests; bootstrap g interval; primary test; in-memory family adjustment; interpretation; saves only with create permission; returns `persisted`, `metric_name`, `sequence_scope`, `standardized_effect_ci`, `primary_test`, `interpretation`, `multiplicity`. Episode-level path also respects permission. New `_interpret`, `_latest_primary_results` (raw p from diagnostics), `_family_adjustment`, `apply_family_adjustment`, `evaluate_experiment_interpretation` (TOST matched by run IDs; adjusted p only with a family), `compute_power_grid`. `compute_power_analysis` takes seed and design and returns the Monte Carlo error; `compute_required_sample_size` takes a seed. Replication and jackknife use scoped names. Results table export gains eleven columns. |
| `eorl_lab/api/process.py` | `_run_level_metric_json` reads only rows newer than the run. `get_process_explorer_data(run, scope)`: DFG, variants, swimlane with category and choice, summary, actor and functional continuity and `path_coherence_v1`. `get_adaptation_view_data`: per-episode utility, chosen supplier, viability and pre-shock membership; repertoire and shock-adaptation summaries. Survival analysis on utility. Role checks added. |
| `eorl_lab/api/experiments.py` | `launch_pilot` passes `actor_engine`, `experiment` and `cell_id`. New `estimate_experiment_cost`. |
| `eorl_lab/api/runs.py`, `api/traces.py`, `api/exports.py` | Role checks on `list_runs`, `get_run_detail`, `get_branch_history`, `list_branch_groups`, `list_episodes`, `get_episode_trace`, `export_run_bundle`. |
| `eorl_lab/providers/deterministic.py` | `_choose_supplier` parses `ordered_from:X;quality:...`. New hook methods `_choose_supplier` and `_wants_check`; the PO review, PO confirmation and receipt confirmation reads go through `_wants_check`. Order-to-cash policies for Sales, Fulfillment, Billing and General Order agents (`_o2c_next` and step lists). |
| `eorl_lab/providers/factory.py` | `ACTOR_ENGINES`, `engine_type_of`, `engine_override` argument, `bounded_rational` provider. `llm` refuses a non-generative profile. |
| `eorl_lab/providers/openai_compatible.py`, `providers/base.py` | Latency measured per call, `retry_count` on `ModelResponse`. |
| `eorl_lab/observability/context.py` | `telemetry`, `expected_denial_codes`, `engine_override` on `ExperimentContext`. |
| `eorl_lab/observability/exporter.py` | Manifest adds experiment, cell, routine, engine, scenario snapshot, code commit at launch, failure type, telemetry. Scenario stream uses the run's generator and outcome model. |
| `eorl_lab/observability/replay.py` | Reproduces with the original outcome model (`receipt_keyed_v1` when no snapshot) and scripted or bounded-rational engine. |
| `eorl_lab/hooks.py` | `app_include_js = "/assets/eorl_lab/js/eorl_export.js"`. |
| `eorl_lab/install.py` | `after_install` also runs the v2 construct update and routine seeding. |
| `eorl_lab/patches.txt` | Three v2 patches added. |

#### Changed DocType schemas

| DocType | Fields added or changed |
|---|---|
| EORL Experiment | `experiment_type`, `demonstration`, `actor_engine`, `interpretation_combination`. |
| EORL Analysis Plan | `sequence_scope`, `adjustment_method`, `random_seed`; section Registered Interpretation with `expected_direction`, `rival_prediction`, `support_rule`, `contradiction_rule`, `equivalence_rule`, `inconclusive_rule`, `trivial_effect_rule`, `interpretation_weight`. |
| EORL Analysis Result | `sequence_scope`, `family_id`, `adjustment_method`, `is_primary_test`, `effect_size_ci_low`, `effect_size_ci_high`, `effect_size_ci_method`, `interpretation_label`, `undefined_fields`; `p_value` relabeled "Raw p-value". |
| EORL Construct | `status`; labels Measurement Definition, Manipulation Definition, Known Validity Limits. |
| EORL Run | `experiment`, `cell_id`, `routine_template`, `actor_engine`, `failure_type`, `retryable`, `retry_count`, `input_tokens`, `output_tokens`, `model_calls`, `wallclock_seconds`; status option `cancelled`. |
| EORL Episode | `utility`, `failure_type`. |
| EORL Metric | `value_undefined`. |
| EORL Architecture | `routine_template`, `stage_gated_tools`. |
| EORL Model Profile | provider option `bounded_rational`; `base_url` and `api_key_reference` at permission level 1, with level-1 read/write for System Manager, EORL Administrator, EORL Researcher. |
| EORL Settings | section Reviewer Walkthrough, `reviewer_walkthrough_json`. |

#### Changed pages

| Page | Change |
|---|---|
| EORL Lab | Reviewer banner; Building blocks (15 links, Routine Templates and Process Grammars added); Studio list adds Reviewer and Evaluation Matrix; Demonstrations section filtering experiments by demonstration and type. |
| Process Explorer | Scope selector, summary cards, continuity and coherence table, variant table, utility column, supplier shown under the step, export, deep link from `route_options`. |
| Adaptation View | Utility chart with viability-threshold marker, repertoire and shock-adaptation tables, supplier, viable and pre-shock-repertoire columns, export, deep link. |
| Scientific Cockpit | Read-only notice, g with its interval and method, metric and primary test, interpretation card with family, raw and adjusted p, p below 0.0001 in scientific notation, run and plan links, export. |
| Power Planner | Design, alpha, simulations and seed inputs; power table over effects and n with Monte Carlo errors; seeded required-N; export. |
| Trace Explorer | Success and failure marks only on outcome-bearing event types; the failed-only filter follows the same rule. |
| Experiment Studio | Cost and runtime estimate; Queue All Runs button. |

#### Tests

| File | Change |
|---|---|
| `eorl_lab/eorl_lab/doctype/eorl_run/test_eorl_submission_day.py` | New, 42 tests: sequence scopes (5), attribute coherence (2), repertoire and adaptation (3), construct measures and registry (5), inference (6), scenario and outcome model (4), bounded-rational engine (3), failure taxonomy and stage gate (2), integration (12: matched outcomes, order-to-cash, matched tools and telemetry, memory manipulation, expected and unexpected denials, queue and cancellation, Viewer DocPerm, no persistence without permission, family adjustment, interpretation with no family, undefined metric flag, success rate not utility). |
| `test_eorl_construct_registry_and_factorial_experiments.py` | The unimplemented-construct test uses Formalization. |
| `test_eorl_ground_truth_and_authority.py` | The grammar test skips stages outside its fixture. |

#### Documentation and release files

| File | Change |
|---|---|
| `README.md` | Rewritten to answer the six questions the plan lists, with a document table and the release tag. |
| `QUICKSTART.md`, `REVIEWER_GUIDE.md`, `ARCHITECTURE.md`, `REPRODUCIBILITY.md`, `LIMITATIONS.md`, `CHANGELOG.md`, `CITATION.cff`, `LICENSE` | New (the license file names the author; `license.txt` is unchanged). |
| `artifact_manifest.json` | New, from `scripts/generate_artifact_manifest.py`: 182 tests counted and passing, 27 DocTypes, 17 pages, 41 whitelisted functions, capability lists. Currently records commit 5ddf352 and a dirty tree; the freeze script regenerates it. |
| `scripts/generate_artifact_manifest.py`, `scripts/freeze_release.sh` | New. The script refuses a dirty tree, writes the manifest, commits it alone and creates the annotated tag; it does not push. |
| `release/stage1_test_run.log` | New: the final `Ran 182 tests in 530.432s ... OK` log. |
| `docs/guide/stage1-additions.md` | New guide page, added to `mkdocs.yml`. |
| `docs/index.md` | Framed as research infrastructure; Demonstration 1 named as a use. |
| `docs/reference/analysis.md`, `api.md`, `providers.md`, `scenarios.md` | New modules added to the API reference. |
| `docs/doctypes/*.md` | Regenerated by `docs/gen_doctype_docs.py` (28 pages, one new). `mkdocs build --strict` passes. |
| `docs/history/progress.md` | Copy of this file. |
| `pilot/` | Unchanged; still untracked and ready to commit. |
| `EORL_SUBMISSION_DAY_IMPLEMENTATION_PLAN.md` | The plan itself, untracked. |

#### Changes to site data

| Site | Change |
|---|---|
| `erpnext.localhost` | Migrated three times. Patches seeded the routine templates, grammars and two customers and updated the Construct Registry; the backfill patch set engine and routine on older runs. `EORL-O2C-TUB` is created by the tests' setup. Smoke and debug runs were rolled back. |
| `eorl-demo.localhost` | Migrated three times. `setup()` created the SD and O2C profiles, policies, agents, architectures, the regime shift "Supplier Quality Reversal at Episode 7", experiments SD-A to SD-D and seven Analysis Plans, and set `experiment_type` on the two existing experiments. Runs RUN-00034 to RUN-00077. Two analysis batches (the first superseded). The SD runs' metrics were recomputed after the success-rate fix. `reviewer_walkthrough_json` set. The reviewer account's roles were not changed. |

### Tests

The full suite was run on 2026-11-01 on `erpnext.localhost` after the last code change:
`Ran 182 tests in 530.432s ... OK` (log in `release/stage1_test_run.log`). 140 tests
existed before the build; 42 are new, in `test_eorl_submission_day.py`. Two
older tests were changed because the facts they pinned changed on purpose: the
unimplemented-construct test now uses Formalization (Centralization gained a
measure), the grammar test skips stages outside its fixture (finish_turn and
order-to-cash tools).

---

## Commit timeline

23 commits on `main`. The net diff from the scaffold commit to HEAD is 259
files changed, 22,033 insertions and 1 deletion. The per-commit columns count
every change a commit made, so their sums are larger. Dates are the calendar
dates recorded in each commit. Commits carry either a +0000 or a -0700 offset
depending on the shell that made them, so clock times in git are not monotonic
along the commit order, and some evening commits show the previous day
compared with UTC.

| # | Commit | Date | Files | Added | Removed | Subject |
|---|---|---|---|---|---|---|
| 1 | a35e74e | 2026-10-29 | 15 | 272 | 0 | Initialize app (bench scaffold) |
| 2 | 4466366 | 2026-10-29 | 27 | 505 | 0 | Milestone 1: skeleton, roles, config DocTypes, lab page |
| 3 | 4841dc2 | 2026-10-29 | 26 | 900 | 0 | Milestone 2: vertical slice |
| 4 | da20eb0 | 2026-10-29 | 6 | 701 | 166 | Milestone 3: multi-agent routine |
| 5 | 91f77ea | 2026-10-29 | 14 | 632 | 92 | Milestone 4: memory and repeated episodes |
| 6 | 3cc222a | 2026-10-29 | 13 | 762 | 131 | Milestone 5: architectures and shock |
| 7 | 86687d2 | 2026-10-29 | 1 | 250 | 0 | Add PROGRESS.md (Milestones 1 to 5) |
| 8 | 60e45dd | 2026-10-29 | 26 | 1215 | 21 | Milestone 6: research front end |
| 9 | 93fbc5f | 2026-10-29 | 15 | 1097 | 27 | Milestone 7: process paths and theory metrics |
| 10 | ffc18a4 | 2026-10-29 | 7 | 696 | 21 | Milestone 8: reproducibility artifact |
| 11 | 3da0bc9 | 2026-10-29 | 3 | 4370 | 0 | Add SOTA_ROADMAP.md, version both spec documents |
| 12 | cfeeb38 | 2026-10-29 | 37 | 1095 | 90 | SOTA Milestone 1 |
| 13 | 3e1b00b | 2026-10-29 | 10 | 690 | 13 | SOTA Milestone 2 |
| 14 | d32e9f7 | 2026-10-29 | 13 | 1078 | 26 | SOTA Milestone 3 |
| 15 | 3386786 | 2026-10-29 | 17 | 810 | 55 | SOTA Milestone 4 |
| 16 | 9f2bd9e | 2026-10-29 | 54 | 2687 | 1 | Documentation website and Pages workflow |
| 17 | c5d5adf | 2026-10-30 | 26 | 1308 | 29 | SOTA Milestone 5 |
| 18 | 1025851 | 2026-10-30 | 9 | 803 | 77 | SOTA Milestone 6 |
| 19 | 16aa6dd | 2026-10-30 | 16 | 784 | 33 | SOTA Milestone 7 |
| 20 | 164b891 | 2026-10-30 | 15 | 887 | 33 | SOTA Milestone 8 |
| 21 | 36f5b1e | 2026-10-30 | 14 | 707 | 22 | SOTA Milestone 9 |
| 22 | cd984f1 | 2026-10-30 | 19 | 961 | 61 | SOTA Milestone 10 |
| 23 | 9038eac | 2026-10-30 | 13 | 362 | 370 | Docs quality pass |

---

## What exists now (inventory)

Counted from the repository on the lab machine on 2026-11-01.

**Size.** 9,460 lines of Python in total: 5,375 in the application packages
below, 3,876 in tests and 208 in DocType controllers. 1,778 lines of
JavaScript for the Desk pages and 1,113 lines of DocType JSON.

### DocTypes (27)

| Introduced | DocTypes |
|---|---|
| Milestone 1 | EORL Settings (single), EORL Model Profile, EORL Memory Profile, EORL Tool Policy, EORL Allowed Tool (child), EORL Agent Template |
| Milestone 2 | EORL Run, EORL Episode, EORL Event (append-only: the controller rejects edits and deletes) |
| Milestone 4 | EORL Memory Record |
| Milestone 5 | EORL Architecture, EORL Architecture Actor Slot (child), EORL Regime Shift |
| Milestone 6 | EORL Experiment |
| Milestone 7 | EORL Metric |
| SOTA 1 | EORL Communication Policy, EORL Communication Edge (child), EORL Process Grammar, EORL Process Stage (child), EORL Process Transition (child), EORL Task Assignment |
| SOTA 2 | EORL Branch |
| SOTA 4 | EORL Construct, EORL Experiment Factor (child) |
| SOTA 5 | EORL Analysis Plan, EORL Analysis Result |
| Submission day | EORL Routine Template |

20 standalone DocTypes, 6 child tables, 1 single. Roles `EORL Researcher`,
`EORL Administrator` and `EORL Viewer` ship as fixtures. The only data
shipped in code is those roles and the 8 constructs seeded by the patch
`eorl_lab.patches.v1_seed_initial_constructs`. `bench install-app` marks every
patch as already run without running it, so a fresh site never got the
constructs until 2026-11-01, when an `after_install` hook (`eorl_lab/install.py`)
began calling the same function. The `Demo ...` agents,
architectures, regime shifts and experiments used in this document live in
the site database. A fresh install would not have them.

### Desk pages (17)

| Page | From | Purpose |
|---|---|---|
| EORL Lab (`eorl-lab`) | Milestone 1 | Home page linking the config DocTypes and every page below |
| Experiment Studio | Milestone 6 | Pick a saved experiment, see cell and run counts, validate, launch a pilot |
| Run Monitor | Milestone 6 | Live run status, click through to the trace |
| Trace Explorer | Milestone 6 | Run, episode, then chronological event table with filters and expandable payloads |
| Compare Runs | Milestone 6 | Side-by-side aggregates and the computed metric set |
| Reproducibility | Milestone 6, extended in 8 | JSON export, full 14-file bundle, reproduce and verify |
| Scientific Cockpit | SOTA 5 | Compare two groups of runs under an Analysis Plan |
| Process Explorer | SOTA 7 | Directly-follows graph and episode swimlane |
| Network Explorer | SOTA 7, extended in 9 | Agent-message network, QAP comparison |
| Adaptation View | SOTA 7 | Event-study view around a regime shift |
| Power Planner | SOTA 8 | Power and required sample size |
| Robustness Diagnostics | SOTA 8 | Leave-one-run-out and cumulative stability |
| Survival Analysis | SOTA 9 | Kaplan-Meier time to recovery |
| Paired-Branch Inference | SOTA 10 | Sibling-branch picker feeding the paired test |
| Theory Compiler | SOTA 10 | Scaffold an Experiment and an Analysis Plan from a theory |
| Reviewer: Start Here (`eorl-reviewer`) | Submission day | Eleven-step guided walkthrough resolved to real records |
| Evaluation Matrix (`eorl-evaluation-matrix`) | Submission day | Special-issue criteria, evidence, verification path, limitation |

### Whitelisted API (41 functions in `eorl_lab.api`; 29 before the submission-day build)

| Module | Functions |
|---|---|
| `runs` | `launch_demo_episode`, `list_runs`, `get_run_detail`, `branch_run`, `get_branch_history`, `mark_ablation`, `list_branch_groups` |
| `traces` | `list_episodes`, `get_episode_trace` |
| `experiments` | `get_experiment_summary`, `validate_experiment`, `launch_pilot`, `compile_theory` |
| `metrics` | `compute_run_metrics`, `compare_runs` |
| `exports` | `export_run_bundle`, `download_full_bundle`, `reproduce_run` |
| `analysis` | `compare_groups`, `export_results_table`, `compute_power_analysis`, `compute_required_sample_size`, `compute_replication_diagnostics`, `compute_robustness_jackknife`, `compute_qap_comparison` |
| `process` | `get_process_explorer_data`, `get_network_explorer_data`, `get_adaptation_view_data`, `get_survival_analysis_data` |
| Added on submission day | `analysis.apply_family_adjustment`, `analysis.evaluate_experiment_interpretation`, `analysis.compute_power_grid`, `experiments.estimate_experiment_cost`, `queue.enqueue_run`, `queue.enqueue_experiment`, `queue.cancel_run`, `queue.list_queue`, `reviewer.get_reviewer_walkthrough`, `reviewer.get_artifact_manifest`, `reviewer.get_evaluation_matrix`, `reviewer.compare_run_configurations` |

### Semantic ERP tools (26 in the registry; 15 before the submission-day build)

| Kind | Tools |
|---|---|
| Read | `get_supplier_options`, `get_purchase_order`, `get_receipt_status` |
| Write (create, then submit) | `create_purchase_order`, `submit_purchase_order`, `create_purchase_receipt`, `submit_purchase_receipt`, `create_purchase_invoice`, `submit_purchase_invoice`, `create_payment_entry`, `submit_payment_entry` |
| Ground-truth driven (SOTA 1) | `inspect_received_goods`, `escalate_quality_exception` |
| Communication (SOTA 1) | `message_agent` |
| Control (SOTA 3) | `finish_turn` |
| Order-to-cash (submission day) | `get_customer_order`, `get_sales_order`, `get_delivery_status`, `create_sales_order`, `submit_sales_order`, `create_delivery_note`, `submit_delivery_note`, `create_sales_invoice`, `submit_sales_invoice`, `create_customer_payment`, `submit_customer_payment` |

Receipts, invoices and payments are created through ERPNext's own mapper
functions, so tax, account and unit-of-measure resolution match what a user's
"Make" button produces.

### Event types (27)

`run_initialized`, `run_branched`, `run_marked_ablation`, `episode_initialized`,
`environment_observed`, `agent_context_built`, `memory_query`,
`memory_retrieval`, `memory_write`, `agent_message_sent`,
`agent_message_received`, `model_request`, `model_response`,
`decision_parsed`, `tool_requested`, `tool_authorized`, `tool_denied`,
`tool_result`, `soft_rule_violation`, `task_assigned`, `erp_state_before`,
`erp_mutation`, `erp_state_after`, `episode_outcome`, `metric_computed`,
`error`, `run_completed`.

Each event is a row in `EORL Event` with a trace, span, parent span and
correlation id, and a SHA-256 hash of its payload.

### Runtime pieces

| Piece | What it is |
|---|---|
| Architectures | `specialist_handoff` (four actors, orchestrator-enforced handoffs) and `broad_autonomy` (one actor, no handoffs), chosen by the `coordination_mode` field. Callers never name a Python function per architecture. |
| Authority firewall | `eorl_lab.runtime.authority.evaluate`. Runs outside the model on every tool call. Tool must be in the actor's policy, `may_submit_documents` is enforced, hard constraints block, soft rules log a `soft_rule_violation`. Execution and approval limits are enforced. Decision and assignment rights are recorded but not enforced. |
| Providers | `deterministic` (scripted) and `openai_compatible` (any OpenAI-style endpoint with tool calling). `anthropic` appears as an option on the model profile but raises `NotImplementedError`. |
| Memory | `none`, `recent`, `episodic`, `semantic`, `procedural`. `shared` and `vector` raise `NotImplementedError`. |
| Scenario | One procure-to-pay case, `generate_case(seed, episode, regime_shift)`, a pure function of its inputs. Latent supplier quality and price are never placed in a prompt, and a test asserts this. |
| Regime shift | Demand-quantity multiplier from a trigger episode. It is not announced to the agents. |
| Analysis | Pure functions over exported event data, with no Frappe calls: paths, sequence, coherence, repertoire, recovery, networks. The statistics engine in `analysis/stats.py` wraps scipy, statsmodels and lifelines. |
| Export and replay | `observability/exporter.py` builds the 14-file bundle. `observability/replay.py::reproduce_run` re-runs a recorded run and checks scenario hashes and metrics. |

### Python code by package

| Package | Lines |
|---|---|
| `runtime` (orchestrator 945, authority 104) | 1,049 |
| `api` | 1,247 |
| `analysis` (stats 458) | 880 |
| `providers` | 672 |
| `observability` | 449 |
| `memory` | 311 |
| `erp` | 280 |
| `scenarios`, `organization` | 111 |
| `hooks.py` (221), `patches` (135), `config` (20) | 376 |

### Documentation site and CI

`https://agrimsachdeva.github.io/eorl_lab/`, built with MkDocs Material and
mkdocstrings. 12 guide pages, 9 API reference pages (plus an index), 26 DocType pages
generated from the DocType JSON (plus an index), and two history pages. The history pages
(`docs/history/progress.md` and `docs/history/sota-roadmap.md`) are copies of
this file and of `SOTA_ROADMAP.md`. The workflow `.github/workflows/docs.yml`
regenerates the DocType pages, runs `mkdocs build --strict` and deploys on
pushes to `main` that touch docs, `mkdocs.yml`, Python files or DocType JSON.
Both spec documents are versioned in `docs/specs/`.

---

## Reference runs

These exist in the site database on the lab machine only. A fresh install would not have
them. The runs below are on `erpnext.localhost`. The hosted demo site has its
own numbering, listed in "After SOTA 10: hosted demo and language-model
pilot" (RUN-00017 to RUN-00032 there are the pilot).

| Record | Milestone | What it shows |
|---|---|---|
| PUR-ORD-2026-00446 | 2 | First real Purchase Order from an agent, 22-event trace, no gaps |
| PUR-ORD-2026-00447, MAT-PRE-2026-00418, ACC-PINV-2026-00217, ACC-PAY-2026-00109 | 3 | Full chain, all four submitted, 119 events |
| RUN-00006 and RUN-00007 | 6, 7 | Specialist vs broad autonomy on the same seeds. Actor continuity 0.686 vs 1.0 |
| RUN-00010 | 8 | Reproduction of RUN-00006: scenario stream and metrics both matched |
| RUN-00012 | SOTA 1 | 30 scripted episodes with ground-truth-driven exceptions, first non-zero variety |
| RUN-00072, RUN-00073, RUN-00074 | SOTA 2 | One parent branched into two children at episode 2 |
| RUN-00083 | SOTA 3 | One model-driven procure-to-pay episode, 11 tool calls |

---

## Test coverage

182 tests, all passing, in 22 test files (140 before the submission-day build). Run with
`bench --site erpnext.localhost run-tests --app eorl_lab`.

**Original V1 files (33 tests).**

| File | Tests | Milestone |
|---|---|---|
| `test_eorl_settings.py`, `test_eorl_agent_template.py` | 1 + 1 | 1 |
| `test_eorl_run.py` (includes an authority-denial test) | 2 | 2 |
| `test_eorl_multi_agent_routine.py` (includes a submit-rights-denial test) | 2 | 3 |
| `test_eorl_memory_and_repeated_episodes.py` (memory causality, no-profile case) | 2 | 4 |
| `test_eorl_architectures_and_shock.py` (paired-seed and shock acceptance test) | 3 | 5 |
| `test_eorl_experiment_studio_apis.py` (cell and run counts, validation, full paired pilot) | 3 | 6 |
| `test_eorl_process_metrics_synthetic.py` (every formula against hand-computed values) | 14 | 7 |
| `test_eorl_process_metrics_integration.py` (real runs through the real metrics pipeline) | 2 | 7 |
| `test_eorl_reproducibility.py` (bundle contents, reproduction, refusal for old runs) | 3 | 8 |

**SOTA files (107 tests).**

| File | Tests | Milestone |
|---|---|---|
| `test_eorl_ground_truth_and_authority.py` | 13 | SOTA 1 |
| `test_eorl_counterfactual_branching.py` | 6 | SOTA 2 |
| `test_eorl_llm_provider.py` | 12 | SOTA 3 |
| `test_eorl_memory_expansion.py` | 5 | SOTA 3 |
| `test_eorl_construct_registry_and_factorial_experiments.py` | 15 | SOTA 4 |
| `test_eorl_analysis_engine.py` | 13 | SOTA 5 |
| `test_eorl_analysis_engine_phase2.py` | 12 | SOTA 6 |
| `test_eorl_process_and_network_explorer.py` | 5 | SOTA 7 |
| `test_eorl_power_and_robustness.py` | 12 | SOTA 8 |
| `test_eorl_qap_and_survival.py` | 9 | SOTA 9 |
| `test_eorl_paired_branch_ui_and_theory_compiler.py` | 5 | SOTA 10 |

Per-milestone totals above are computed from the test files and add up to the
cumulative counts reported at the end of each milestone from Milestone 7 on
(30, 33, 46, 52, 69, 84, 97, 109, 114, 126, 135, 140). A few per-file counts in the prose of
`SOTA_ROADMAP.md` differ (it says 9 for the memory expansion tests and 15 for
the QAP and survival tests). The files contain 5 and 9, which is the only
reading consistent with those cumulative totals.

Tests that changed meaning along the way. SOTA Milestone 1 made 12 existing
tests fail with `TOOL_NOT_IN_POLICY`, because their policy fixtures
predated the new tools. Six test files were patched. One test was rewritten:
the Milestone 7 integration test used to assert that routine variety is always
zero on live data, and Milestone 1 made that false on purpose.

---

## Problems found and fixed along the way

These are the defects and process mistakes that cost real time. Each is
described in more detail in the milestone it came from.

| Milestone | Problem | Fix |
|---|---|---|
| SOTA 1 | Adding required tools to two agents broke 12 existing tests, whose tool-policy fixtures predated the tools (`TOOL_NOT_IN_POLICY`). | Added the three new tools and `may_message_agents` to the fixtures in 6 test files. Relaxed one exact-count assertion that a quality exception now legitimately changes. |
| SOTA 2 | The scripted provider never passed a purchase rate, so ERPNext fell back to `last_purchase_rate`, which is set from each submitted transaction's own rate. Once one transaction resolved to 0, every later run on the site inherited rate 0 and failed at Payment Entry. | Passed the supplier's real price explicitly and repaired the corrupted rate data. |
| SOTA 3 | The same rate problem returned as soon as a model (which cannot know a hidden price) called `create_purchase_order`. | Fixed at the root: `erp.buying.create_purchase_order` resolves the rate from the scenario's price when the caller supplies none. |
| SOTA 3 | `provider.generate()` was never wrapped in error handling, so a timeout or a malformed tool call from a real model would crash the run. | Failures are caught and logged as an `error` event and a failed episode, the same as a bad tool call. |
| SOTA 3 | Qwen3 can spend its whole token budget reasoning and return no tool call. | A model profile can turn thinking off through the vLLM `enable_thinking` setting. The live test keeps thinking on, because with it off the model skipped steps and named a document it had not created. |
| SOTA 5 | A hand-written permutation test converged to p of about 0.048 against an exact-enumeration value of 0.056 on a textbook dataset. | Switched to scipy, which matched the exact value, and adopted "use existing packages" as a standing rule. |
| SOTA 6 | The mixed-effects optimizer emits convergence warnings on zero-variance input, which is what every current episode record is. | Warnings suppressed at the source. The `converged` field in the result still carries the signal. |
| SOTA 7 | The full regression suite (about five minutes) was truncated without any error over the SSH to `docker exec` to `bench` pipe. | Detach the run on the remote host and poll for a completion marker with short SSH calls. |
| SOTA 7 | The live Qwen integration test can fail once when the model returns `finish_reason="length"`. | Known and documented. A retry passes, so a single failure of that test is not a regression. |
| SOTA 8 | A live demo script run through `bench execute` while the background test suite was running deadlocked on the MySQL naming-series table and disturbed the live Qwen test. | A clean rerun passed 126/126. Rule: never run a second bench process against the site while a test run is in flight. |

---

## V1 gap list: status today

The list at the end of the original Milestone 8 write-up, checked against the
code on 2026-11-01.

| Original gap | Status | Detail |
|---|---|---|
| `EORL Scenario` DocType and a distributional scenario generator | Partly addressed, still open | SOTA 1 made ground truth drive inspection and price outcomes. There is still no `EORL Scenario` DocType. The generator is code in `scenarios/procurement.py`: one procure-to-pay case with demand variation. Only quality exceptions exist. |
| Experiment limited to one factor, two levels | Closed (SOTA 4) | `EORL Experiment Factor` gives N-factor designs. Old two-architecture experiments still work. |
| Agent Studio, Architecture Designer, Scenario Studio | Open | Agents and architectures are still composed in plain DocType forms. The Theory Compiler scaffolds an Experiment and an Analysis Plan but does not compose agents. |
| Variety, repertoire and adaptation metrics have nothing to discriminate on | Variety closed (SOTA 1). Adaptation still open on live data | Ground truth now produces a second process variant. The demand shock still changes quantity but not success, so adaptation and repertoire metrics are flat on live data. |
| Counterfactual replay from a changed configuration or a specific episode | Closed with a caveat (SOTA 2) | `branch_run` and `EORL Branch`. ERP documents are not forked, so only process-trace comparisons are valid across branches. |
| `EORL Run` has no link to `EORL Experiment` | Open | Run manifests still carry no experiment id or cell id. |
| External or HPC workers, Parquet export, isolated concurrent environments | Open | Launches run synchronously inside the request. There is no queue, no Parquet writer and no per-branch site clone. |
| Agent-initiated `message_agent`, `request_approval`, `escalate_exception` | Mostly closed (SOTA 1) | `message_agent` is checked against an `EORL Communication Policy` graph, and `escalate_quality_exception` exists. There is no `request_approval` tool. The specialist architecture's handoffs are still orchestrator-enforced. |
| `erp_research` migration and parity (spec section 25) | Not started, not needed | `eorl_lab` has no references to `erp_research`. Parity was never checked. |
| Pages not exercised in a browser | Partly closed | On 2026-10-31, at least seven pages were opened in a headless browser against live data while preparing the Stage 1 submission (Scientific Cockpit, Process Explorer, Adaptation View, Survival Analysis, Trace Explorer, Power Planner and Network Explorer), and Experiment Studio was exercised through its validation call. Four defects turned up (below). The remaining pages have not been browser-tested systematically. |

---

## Open items today

### Status after the submission-day build

Resolved on 2026-11-01 (details in "Submission-day build"): the demand
shock that did not change success (a supplier-quality reversal now
exists); no non-generative baseline (bounded-rational engine); 2 of 8
executable constructs (now 9 of 12); attribute-level coherence not
measured; no multiple-testing correction; two-group-only power planning
(paired design added); EORL Run not linked to its experiment; no queued
execution; the unseeded Power Planner page; p-values shown as 0.0000; the
Trace Explorer red cross; the missing role checks; the reviewer able to
read the model endpoint; reviewer comparisons writing Analysis Result
rows; `pilot/` untracked (committed with this build); no second routine.

Still open from the lists below: Mann-Whitney, Wilcoxon and Cox models;
mixed effects beyond success rate; Experiment Studio's "architecture_a is
required" on Theory Compiler drafts;
external workers and Parquet export; `anthropic`, `shared` and `vector`;
`request_approval` and enforcement of decision and assignment rights;
graphical studios; per-branch ERP isolation; a second model family; the
decision-confidence placeholder; temporal motifs and sequence clustering.
The Word submissions in `~/eorl_docx_updated/` predate this build.

Found at the end of the build, not changed:

- **The reviewer account is not read-only.** On `eorl-demo.localhost`,
  `reviewer@example.org` holds `EORL Researcher` as well as `EORL Viewer`
  (the Researcher role was added by Administrator at 06:49 on 2026-11-01).
  With it the account can create and edit EORL records and its comparisons
  are saved. Every read-only statement in the documents assumes the Viewer
  role alone. Remove the Researcher role before sharing the login.
- **The live servers still run the code from before the build.** They are
  started with `--noreload`; restart them with `~/eorl_live/eorl_live_ctl.sh
  stop` and `start` so the hosted site serves the new pages and endpoints.
- **The public site runs Frappe's development server.** `bench serve` starts
  Werkzeug with its debugger on. Werkzeug 3.1.5 allows the debugger console
  only for a `.localhost` or `127.0.0.1` Host and only with the PIN, and a
  console also needs the per-process secret shown on a crash page, so the
  exposure is small. Starting the port-8002 server with the debugger off
  would remove it; setting `CI=1` is not a safe way to do that, because it
  also makes Frappe's guest-callable `can_subscribe_doc` skip its permission
  check.
- **The background queue needs a worker** (`bench worker --queue long`); the
  live supervisor starts web servers only.


### Science and design

- The demand shock does not change success, so adaptation and repertoire
  metrics are flat on live data. A shock that invalidates previously
  successful paths (for example a change in latent supplier quality) is the
  first thing needed for an adaptation study.
- One regime is implemented: bounded discretion. There are no random,
  rule-based or bounded-rational baseline engines, so a claim that a
  mechanism depends on generative models cannot yet be tested.
- One process, four actors and one ERP system. Quality exceptions are the only
  exception family. Delivery, invoice and approval exceptions are not built.
- Branch children share one company, so ERP aggregates such as stock levels
  are not comparable across branches.
- 2 of the 8 registry constructs have executable measures.
- The continuity metrics are proxies. The attribute-level path coherence of
  Kim et al. (2024) is not measured. QAP is coarse with four actors (the
  smallest attainable p is 1/24). Temporal motifs and sequence-distance
  clustering are not built.
- Inference: no multiple-testing correction, no Mann-Whitney, Wilcoxon or Cox
  model, power planning covers only the two-group Welch design, and the
  mixed-effects model covers success rate only.
- Model-driven runs are not reproducible exactly, and `reproduce_run` works
  only for scripted runs launched through `run_architecture`. The only
  multi-run model evidence is the 16-run pilot (8 per architecture, one model,
  one routine, one scenario), which is small and has the confound described
  above.
- Decision confidence is a fixed placeholder (0.7).

### Engineering

- Link `EORL Run` to `EORL Experiment` and record experiment id and cell id in
  the manifest.
- Queued or background execution, external workers, Parquet export.
- `anthropic` provider; `shared` and `vector` memory backends.
- `request_approval` tool; enforcement of decision and assignment rights in
  the authority firewall.
- `EORL Scenario` DocType; Agent Studio and Architecture Designer.
- Demo records exist only in the site database. Shipping them as fixtures or a
  seed patch would let a fresh install reproduce the reference runs.

### Found in the 2026-10-31 browser pass

- **Power Planner is not seeded from the Desk page.** Repeated clicks with the
  same inputs gave 81.5%, 81.6% and 84.0% power at 27 runs per group (effect
  0.8). The API accepts a seed; the page does not pass one.
- **Welch p-values display as 0.0000** in the Cockpit when the stored value is
  below 0.0001 (6.2e-8 in the positive control). Scientific notation below that
  threshold would stop it reading as a rounding bug.
- **Trace Explorer shows a red cross on non-outcome lifecycle events** whose
  success flag is 0. It reads as a failure and is not one.
- **Experiment Studio reports "architecture_a is required"** when validating
  the stored experiment "M10 Demo Theory: Repetition and Coherence". That
  record is a draft that the Theory Compiler scaffolded, and it has no
  architectures yet.

### Found while building the hosted demo and the pilot (2026-11-01)

- **Five whitelisted functions lack a role check** (`frappe.only_for`):
  `list_runs`, `get_run_detail`, `list_episodes`, `get_episode_trace` and
  `compare_groups`. The reviewer role can also read the Model Profile's
  `base_url`. The key itself is in site config and is not readable. Neither
  gap is fixed.
- **No public route for reviewers.** Resolved later on 2026-11-01: the demo
  site is public at `https://enterpriseailab.taile74753.ts.net` through Funnel.
  The Word submissions say a link and reviewer login go in the submission form.
- **`pilot/` is untracked.** The scripts are in the working tree of the repo
  on the lab machine but not committed, and Section 11.4 of the appendix says they are
  in the repository. If the review is double-blind, the package metadata in
  `pyproject.toml` carries the author's name and email.
- **Do not re-run `pilot_analyze.py --full`.** It stores new Analysis Result
  rows, and the pilot's results are already stored. Opening a comparison in
  the Scientific Cockpit also stores a row each time, so the demo has a few
  extra rows from the scripted positive control.
- **Smoke runs RUN-00013 to RUN-00016 stay on the demo site.** RUN-00013
  failed at the model's output-token limit. None enters an analysis.
- **Pilot measures count optional read-only calls**, which is what produced
  the pilot's difference. A future registration should say whether read-only
  tools count in a path.

---

*Last updated: 2026-11-01, after the submission-day build.
The Milestone 1 to 8 sections above are unchanged from 2026-10-29.*
