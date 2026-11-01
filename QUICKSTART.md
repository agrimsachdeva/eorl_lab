# Quickstart

EORL is a Frappe app. It needs a Frappe 14 / ERPNext 14 bench (Python 3.10, MariaDB,
Redis). The commands below run inside the bench directory.

## 1. Install

```bash
bench get-app https://github.com/agrimsachdeva/eorl_lab.git --branch main
bench --site <site> install-app eorl_lab
bench --site <site> migrate
```

`install-app` seeds the Construct Registry, the two routine templates (Procure-to-Pay,
Order-to-Cash) and their process grammars. The routines run against an ERPNext company
with a stock item and two suppliers (procure-to-pay) and two customers (order-to-cash).
The scenario generators name them in `eorl_lab/scenarios/procurement.py` and
`eorl_lab/scenarios/order_to_cash.py`; `pilot/demo_setup.py` creates matching master
data on an empty site, and `order_to_cash.ensure_master_data()` creates the customers.

## 2. Run the tests

```bash
bench --site <site> run-tests --app eorl_lab
```

The suite creates its own fixtures and real ERPNext documents. One test calls a live
language model and is skipped or fails without the endpoint configured; everything else
is scripted. Do not run a second bench process against the same site while the suite runs.

## 3. Run a first experiment (scripted, no model needed)

```bash
# the four demonstration designs: creates architectures, agents, a supplier-quality
# reversal, four typed experiments and their analysis plans, before any run
bench --site <site> execute eorl_lab.demonstrations.submission_day.setup

# order-to-cash, scripted, two architectures x 2 repetitions x 3 episodes
bench --site <site> execute eorl_lab.demonstrations.submission_day.run_experiment --kwargs '{"key": "D"}'
```

Or one run of a named architecture:

```bash
bench --site <site> execute eorl_lab.runtime.orchestrator.run_architecture \
  --kwargs '{"architecture_name": "SD Broad Autonomy", "seed": 7, "episode_count": 6, "actor_engine": "bounded_rational", "regime_shift": "Supplier Quality Reversal at Episode 7"}'
```

## 4. Look at it

Open `/app/eorl-lab` in the Desk. `/app/eorl-reviewer` is the guided walkthrough.
`/app/eorl-process-explorer`, `/app/eorl-adaptation-view` and
`/app/eorl-scientific-cockpit` are the main analysis pages.

## 5. Language-model actors

Create an `EORL Model Profile` with provider `openai_compatible`, a `base_url`, a
`model_name` and an `api_key_reference`, which is the *name* of a site-config key:

```bash
bench --site <site> set-config <api_key_reference> <key>
```

Bind the profile to an Agent Template, or launch with `actor_engine="llm"`. The pilot
scripts in `pilot/` show the full setup used for the Qwen3 pilot.

## 6. Background execution

`eorl_lab.api.queue.enqueue_run` and `enqueue_experiment` queue runs on the `long`
queue. They need a worker: `bench worker --queue long`.
