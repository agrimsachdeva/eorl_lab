# Pilot and demonstration-site scripts

These scripts built the hosted demonstration site and ran the pre-registered
pilot reported in Section 7.4 of the Technical Appendix. They are kept as run.
Each carries the bench path (`/workspace/development/frappe-bench`) and the
site name (`eorl-demo.localhost`) as constants near the top, so adjust those
for a different bench.

| File | Purpose |
| --- | --- |
| `demo_setup.py` | Runs the ERPNext setup wizard for a fictitious company and seeds two suppliers and one stock item (MILK-001). |
| `demo_seed.py` | Seeds scripted architectures, a regime shift, an experiment, an analysis plan, scripted runs, and the read-only reviewer user. Reads `REVIEWER_USER`, `REVIEWER_PASSWORD`, and `ADMIN_PASSWORD` from the environment. |
| `pilot_setup.py` | Creates the Qwen3 Model Profile, five tool policies, five agent templates (with the role instructions used in the pilot), and the two pilot architectures. |
| `pilot_prereg.py` | Stores the pilot Experiment with its hypotheses, and three Analysis Plans with equivalence bounds, before any pilot run. |
| `pilot_smoke.py` | One-episode check of each architecture (seed 9001). Not part of the analysis. |
| `pilot_run.py` | Runs the pilot: 8 paired seeds x 2 architectures x 6 episodes, arm order alternating by repetition, resumable through `pilot_logs/state.json`. |
| `pilot_analyze.py` | Descriptive statistics by default. With `--full` it computes run metrics and applies the three saved Analysis Plans. |

## Order of use

`demo_setup.py` and `demo_seed.py` define functions (`wizard`, `master_data`,
`seed_config`, `seed_pilot`, `seed_analysis`, `seed_long_and_branch`,
`seed_users`, `counts`) that are called from a `bench --site <site> console`
session or with `bench execute`. The pilot files are plain scripts, run with
the bench Python from the `sites/` directory. The order was:

1. `demo_setup.wizard()`, then `demo_setup.master_data()`
2. the `demo_seed.py` functions, in the order listed above
3. `pilot_setup.py`, then `pilot_prereg.py`, then `pilot_smoke.py`
4. `pilot_run.py 8 6 7100` (repetitions, episodes per run, base seed)
5. `pilot_analyze.py`, then `pilot_analyze.py --full`

## Model credentials

The pilot calls an OpenAI-compatible endpoint. The Model Profile stores the
endpoint address and the name of a site-configuration key, never the key.
Put the key in the site's `site_config.json` under that name for the duration
of the pilot and remove it afterwards. Do not commit it.

## Running

Do not run two bench processes that write to the same site at once. Naming
series rows stay locked until commit, and the pilot runner commits only when a
run ends.
