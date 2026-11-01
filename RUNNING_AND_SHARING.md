# Running, testing and sharing EORL Lab

How to start the EORL Lab app on the lab machine (tailnet name `enterpriseailab`), run its tests, look at it from another machine, and (if you decide to) put a live copy on the internet for the *Organization Science* submission.

> **Operator document.** It contains this machine's tailnet IP address and hostname. It is deliberately **not** in `docs/` and **not** in the `mkdocs.yml` nav, because the public docs site is built from those. Read it through before you give anyone access to the repository.

Last updated: 2026-11-01.

> **State at the end of 2026-11-01.** A clean demo site, `eorl-demo.localhost`, is running on the lab machine at `http://100.117.207.117:8002` and is **public** through Tailscale Funnel at **`https://enterpriseailab.taile74753.ts.net`** (section 7). Only the demo site is behind that URL; the working site on 8001 is not. Section 3.4 describes the site, how it was built and how to log in. The login details are in `~/eorl_live/credentials.env` on the lab machine.
>
> **Machine name.** The Tailscale node was renamed from `agrim` to `enterpriseailab` on 2026-11-01. The operating-system hostname and the Linux account are still `agrim`, so paths such as `/home/agrim` and the SSH user are unchanged. The old name `agrim.taile74753.ts.net` no longer resolves.

How to read the status labels:

| Label | Meaning |
|---|---|
| **Verified** | Run on the lab machine (or against it over the tailnet) on 2026-11-01 and the result was as described. |
| **Not tested** | Written from `--help` output, source code or vendor documentation. Nothing was run. Try it once before you rely on it. |
| **Blocked** | Needs something only you (the tailnet owner) can do. |

## Contents

1. [Facts you need](#1-facts-you-need)
2. [Reach the lab machine](#2-reach-the-lab-machine)
3. [Start, check and stop](#3-start-check-and-stop)
4. [Open it in a browser](#4-open-it-in-a-browser)
5. [Run the tests](#5-run-the-tests)
6. [Before anything goes on the internet](#6-before-anything-goes-on-the-internet)
7. [Option A: Tailscale Funnel](#7-option-a-tailscale-funnel)
8. [Option B: Cloudflare quick tunnel](#8-option-b-cloudflare-quick-tunnel)
9. [Option C: no live instance](#9-option-c-no-live-instance)
10. [Anonymity](#10-anonymity)
11. [Credentials](#11-credentials)
12. [Troubleshooting](#12-troubleshooting)
13. [Decisions and open items](#13-decisions-and-open-items)
14. [Appendix A: loopback forwarder](#appendix-a-loopback-forwarder)

## 1. Facts you need

| Item | Value |
|---|---|
| Machine | Tailscale node `enterpriseailab` (OS hostname `agrim`, Linux account `agrim`), Ubuntu, Tailscale IPv4 `100.117.207.117`, tailnet `agrimsachdeva.github`, MagicDNS name `enterpriseailab.taile74753.ts.net`, Tailscale 1.104.2 |
| Repo (host path) | `~/frappe_docker/development/frappe-bench/apps/eorl_lab` |
| Repo (container path) | `/workspace/development/frappe-bench/apps/eorl_lab` |
| Git | remote `upstream`, branch `main`. Run git on the **host** shell, not in the container. |
| Compose file | `~/frappe_docker/.devcontainer/docker-compose.yml`, compose project name `devcontainer` |
| Containers | `devcontainer-frappe-1`, `devcontainer-mariadb-1`, `devcontainer-redis-cache-1`, `devcontainer-redis-queue-1`. All have `restart: unless-stopped`, so they come back after a reboot. |
| Bench | `/workspace/development/frappe-bench` in the container, virtualenv `env`, Python 3.10.12 |
| Versions | Frappe 14.101.1, ERPNext 14.92.14 |
| EORL working site | `erpnext.localhost`, served on port 8001. It is your own development site. It also holds the older erp_research study (106 participant users, `admin@admin.com`, session, task-event and chat-message data, 556 purchase orders). **Never expose this site to the internet.** |
| EORL demo site | `eorl-demo.localhost`, served on port 8002. Built clean for sharing (section 3.4). Public at `https://enterpriseailab.taile74753.ts.net` through Funnel; its `site_config.json` sets `host_name` to `https://enterpriseailab.taile74753.ts.net:443` so links Frappe generates use the public address (the explicit `:443` stops Frappe appending the dev port 8000). |
| Other sites on the bench | `agentic.localhost`, `auto.localhost`, `conversational.localhost` (not used by EORL) |
| Live-instance files on the host | `~/eorl_live/eorl_live_ctl.sh` (supervisor), `~/eorl_live/credentials.env` (mode 600), `~/eorl_live/boot.log`. None of them is in the repo. |
| Published ports | 8000-8005 and 9000-9005, bound to the **tailnet IP only** (compose lines 55-57). They are not reachable on `localhost` of the lab machine and not on the LAN. |
| Web server | The container command is `sleep infinity`, so a running container does not mean a running site. The supervisor in section 3.4 starts the two single-site servers (cron `@reboot`, not yet tested across a reboot). Without it, nothing is serving. |

Frappe picks the site from the HTTP `Host` header. That is why section 4 has two routes.

## 2. Reach the lab machine

```bash
tailscale ssh agrim@enterpriseailab
```

The user is still `agrim`; only the Tailscale host name changed. **Not tested** since the rename.

Tailscale SSH sometimes asks for a browser re-approval and prints a login URL. Only you can open it. Nothing in this document works until that is done.

Enter the container for anything that uses `bench`:

```bash
docker exec -it devcontainer-frappe-1 bash
cd /workspace/development/frappe-bench && source env/bin/activate
```

## 3. Start, check and stop

### 3.1 Containers

They are normally already up (`docker ps` shows four). If not:

```bash
cd ~/frappe_docker && docker compose -f .devcontainer/docker-compose.yml up -d
```

Do not edit the compose file's `ports:` lines casually. A change recreates `devcontainer-frappe-1`, and anything installed inside the container itself (rather than under the `/workspace` bind mount) is lost.

### 3.2 Full development stack

Runs the web server on 8000, socket.io on 9000, the asset watcher, the scheduler and one worker (the `Procfile`).

```bash
# inside the container, in the bench directory, venv active
nohup bench start > logs/bench_start.log 2>&1 &
```

`FRAPPE_BIND_ADDR=0.0.0.0` is already set for the container in the compose file, so the server listens on all interfaces.

Check it (expected to return `{"message":"pong"}`; **Not tested** on port 8000 today):

```bash
curl -s -H 'Host: erpnext.localhost' http://100.117.207.117:8000/api/method/ping
```

Stop it:

```bash
pkill -f "[h]oncho"
```

The brackets matter. Without them `pkill` can match the shell that is running it. A "defunct honcho" line in `ps` output from an old session is harmless.

### 3.3 Single-site server (the one to use for sharing)

**Verified** on 2026-11-01.

```bash
# inside the container, in the bench directory, venv active
nohup bench --site erpnext.localhost serve --port 8001 --noreload > logs/serve_8001.log 2>&1 &
```

What was checked:

- It serves only `erpnext.localhost`, whatever the `Host` header says. A request with `Host: some-other-name.example` returned `{"message":"pong"}` from `/api/method/ping` and HTTP 200 from `/login`.
- From the Jetstream VM, over the tailnet, `http://100.117.207.117:8001` returned pong on `/api/method/ping`, 200 on `/login`, and 301 to `/login?redirect-to=%2Fapp%2Feorl-lab` for an unauthenticated `/app/eorl-lab`. The raw IP works because the host name is ignored.
- It has no socket.io, scheduler, worker or asset watcher. EORL does not call `frappe.enqueue` or `frappe.publish_realtime` anywhere in the app (searched 2026-11-01), so EORL features do not depend on them. Stock ERPNext background features (email queue, scheduled jobs) will not run.

Stop it:

```bash
pkill -f "[b]ench --site erpnext.localhost serve"
```

Do not start a test run while any other `bench` process is up (see section 5).

On the lab machine the supervisor in section 3.4 now runs this same command for you, so use the manual form only for a one-off.

### 3.4 The live demo site and its supervisor

**Verified** on 2026-11-01, except where marked.

**Why a separate site.** `erpnext.localhost` holds the older erp_research study (106 participant users, `admin@admin.com`, session, task-event and chat-message data). A reviewer who can log in to that site is one permission mistake away from participant data. So the instance for sharing is a new, clean site, `eorl-demo.localhost`, with none of that data in it.

**What the site contains.**

| Part | Detail |
|---|---|
| Apps | `frappe`, `erpnext`, `eorl_lab`. Not `erp_research`. |
| ERPNext master data | Company `Hoosier Ice Cream` (abbreviation `HIC`, US dollars, standard chart of accounts), suppliers `Bloomington Dairy` and `Indiana Foods Inc`, item `MILK-001`. The procurement scenario and the tests are written against these names. |
| Reference data | The 8 initial constructs, seeded by the install hook (see "Install bug" below). |
| Configuration records | Profile `Scripted Policy`, architectures `Specialist Handoff` (four actors) and `Broad Autonomy` (one actor), regime shift `Demand Surge at Episode 4` (quantity x1.8), experiment `Specialist vs Broad Autonomy`, analysis plan `Run-level actor continuity`. |
| Runs | `RUN-00001` to `RUN-00010`: the experiment's pilot, 5 paired repetitions of both architectures, 6 episodes each, seeds 100 to 104. `RUN-00011`: one 30-episode specialist run, seed 7. `RUN-00012`: `RUN-00001` branched at episode 2 under Broad Autonomy. `RUN-00013`: a live-model episode that **failed** (see below). `RUN-00014`: a live-model episode that succeeded, seed 43, 4 model requests and 4 tool calls. |
| Analysis | One comparison, `RUN-00001/3/5/7/9` against `RUN-00002/4/6/8/10`. Mean actor continuity 0.709 against 1.000, Welch p = 3.7e-07, permutation p = 0.0079 (the smallest p a 5 against 5 permutation test can give). This is a positive control for the pipeline, not a finding: one actor has actor continuity 1.0 by construction. |
| Volume | 14 runs, 94 episodes, about 12,300 events, and real ERPNext documents behind them: 94 purchase orders, 92 receipts, 92 invoices, 92 payment entries. |
| Users | `Administrator` (a generated strong password) and `reviewer@example.org` (a System User with only the **EORL Viewer** role, no welcome email). Both passwords are in `~/eorl_live/credentials.env`. |
| Site config | Only the database keys. `allow_tests`, `qwen_api_key`, `qwen_base_url`, `qwen_model` and `ai_mode` were set while seeding and tests ran, then removed. |

`RUN-00013` is kept on purpose. The model spent its whole 600-token default budget on reasoning and returned no tool call (`finish_reason='length'`), and the run recorded exactly that as its `failure_reason`. The profile `Qwen3 27B (vLLM)` now has `max_tokens` 4096, which is what `RUN-00014` used.

**Things a reviewer can see.** The model profile `Qwen3 27B (vLLM)` stores the vLLM host's address (a tailnet address) in its `base_url` field. The reviewer can read that DocType. The run records do not carry the address (checked in the database for RUN-00013 and RUN-00014). It is not a secret and is unreachable from outside your tailnet, but it is visible to the reviewer. Edit the profile if you would rather it were not. The API key is **not** stored anywhere in the site.

**What a reviewer can do (Verified with Playwright and system Chrome, from the Jetstream VM over the tailnet, logged in as the reviewer).**

- An unauthenticated request to `/app/eorl-run` redirects to `/login`.
- After login, these pages load with no console errors: EORL Lab, Run Monitor, Scientific Cockpit, Process Explorer, Trace Explorer, Compare Runs, Network Explorer, Adaptation View, Reproducibility. The run list shows 14 runs and `RUN-00001` opens.
- In the Scientific Cockpit, selecting the plan and the two run groups and pressing Compare returned the numbers in the table above, with links to the stored result and its provenance.
- The Experiment Studio returns 403 for the EORL Viewer role. It is a launch tool, so that is the intended result.
- By API: `list_runs` returns 200. `launch_demo_episode` and `launch_pilot` return 403. Reading Purchase Orders returns 403. The user list shows only the reviewer's own record.
- **Not tested:** Power Planner, Survival Analysis, Robustness Diagnostics, Paired-Branch Inference and Theory Compiler pages, and any browser other than Chrome.

**The supervisor.** `~/eorl_live/eorl_live_ctl.sh` runs one single-site server per `site:port` pair in its `SITES` line (today `erpnext.localhost:8001 eorl-demo.localhost:8002`). Each server runs in a loop inside the container, so it comes back five seconds after a crash. A lock per port makes `start` safe to run twice.

```bash
~/eorl_live/eorl_live_ctl.sh status    # prints pong or DOWN for each site
~/eorl_live/eorl_live_ctl.sh start
~/eorl_live/eorl_live_ctl.sh stop
```

The agrim user's crontab has `@reboot /home/agrim/eorl_live/eorl_live_ctl.sh start >> /home/agrim/eorl_live/boot.log 2>&1`. The script waits for the container, then starts the servers. **Not tested** across an actual reboot; check `status` after the next one. Logs are `logs/serve_8001.log` and `logs/serve_8002.log` in the bench.

Stop the supervised servers before a test run (section 5), then start them again.

**Install bug found and fixed.** `bench install-app` marks every entry in `patches.txt` as already run without running it. So a freshly installed site never received the 8 constructs from `v1_seed_initial_constructs`, and a full test run on the new site gave 140 tests, 1 failure and 5 errors, all from the missing constructs. `eorl_lab/install.py` now calls the same function from an `after_install` hook. Checked on a throwaway fresh site (frappe, erpnext, eorl_lab only): 8 constructs after install. The two test modules holding the six failures then ran 15 and 5 tests, all passing. The other 134 tests passed in the first run. A single full run of all 140 on the fixed code has not been done.

**Rebuilding the site.** The build used temporary helper scripts that were not kept. The steps were:

1. `bench new-site eorl-demo.localhost --admin-password <pw> --mariadb-root-password <root pw> --install-app erpnext`
2. ERPNext setup wizard through `frappe.desk.page.setup_wizard.setup_wizard.setup_complete(args)` with language English, country United States, timezone America/Phoenix, currency USD, company `Hoosier Ice Cream`, abbreviation `HIC`, chart `Standard`, domain Manufacturing, fiscal year 2026-01-01 to 2026-12-31, full name `EORL Administrator`. Leave email and password out so `Administrator` is updated.
3. The two suppliers and `MILK-001` (stock item, purchase item, litre, default warehouse `Stores - HIC`, expense account `Cost of Goods Sold - HIC`, cost centre `Main - HIC`).
4. `bench --site eorl-demo.localhost install-app eorl_lab`
5. The configuration records and runs in the table above, created through the app's own functions (`run_architecture`, `launch_pilot`, `branch_run`, `compare_groups`).

`bench execute` takes a dotted path whose **first segment must be an installed app**, so a throwaway helper has to live inside an app's Python package (for example `eorl_lab/_tmp.py`, run as `eorl_lab._tmp.run`) and be deleted afterwards.

## 4. Open it in a browser

### 4.1 From any machine on your tailnet (recommended)

1. Check the servers are up: `~/eorl_live/eorl_live_ctl.sh status` on the lab machine (section 3.4).
2. On the other machine (signed in to the same tailnet) open `http://100.117.207.117:8002/` for the demo site, or `http://100.117.207.117:8001/` for your working site.
3. Log in. For the demo site use `reviewer@example.org` or `Administrator`, with the passwords in `~/eorl_live/credentials.env`. For the working site use the account you already use.
4. The EORL workspace is at `/app/eorl-lab` and links to every page.

**Verified** on the demo site (port 8002): a full browser login as the reviewer, page loads and a Cockpit comparison (section 3.4). Port 8001 was checked with `curl` only (section 3.3).

### 4.2 Full stack on port 8000, with a hosts-file entry

Use this only if you need socket.io, the scheduler or the worker, or the other three sites.

1. Run section 3.2.
2. On the client machine add this line to its hosts file (`/etc/hosts` on macOS and Linux, `C:\Windows\System32\drivers\etc\hosts` on Windows, editing as Administrator):

   ```
   100.117.207.117  erpnext.localhost
   ```

3. Browse to `http://erpnext.localhost:8000/app/eorl-lab`.

**Not tested.** One thing to expect: Chromium-based browsers and Firefox may treat any `*.localhost` name as the local machine and skip the hosts file (RFC 6761 behaviour). If the page does not load, or shows your own machine, use 4.1 instead. Sending the header yourself, as in `curl -H 'Host: erpnext.localhost' http://100.117.207.117:8000/...`, does not depend on the browser.

Opening `http://100.117.207.117:8000` by raw IP is **Not tested**. It depends on Frappe's fallback site, and `common_site_config.json` has `serve_default_site: true` but no `default_site` key.

## 5. Run the tests

Prerequisites:

- `allow_tests` is set in the site config. It is set on `erpnext.localhost`. On `eorl-demo.localhost` it was removed for sharing, so set it first: `bench --site eorl-demo.localhost set-config allow_tests True --parse`, and remove it afterwards (section 6, item 4).
- The vLLM host and key are in the site config as `qwen_base_url`, `qwen_model` and `qwen_api_key`, and the host is reachable. Some tests call the live model. On the demo site these keys were removed too, so copy them in for the run and remove them afterwards.
- No other `bench` process is running. A second bench process during the suite caused a MySQL naming-series deadlock in SOTA Milestone 8. On the lab machine that means `~/eorl_live/eorl_live_ctl.sh stop` first, and `start` afterwards.
- Frappe's runner works against the site's own database. Do not run it while someone is using the site.

```bash
# inside the container, in the bench directory, venv active
bench --site erpnext.localhost run-tests --app eorl_lab
```

Expect about 8 minutes and 140 tests (the count at SOTA Milestone 10). The run on the fresh demo site took 492 seconds.

Detached form, for when you are connected over SSH and do not want a dropped connection to kill it:

```bash
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bash -c \
  'source env/bin/activate && bench --site erpnext.localhost run-tests --app eorl_lab > /tmp/eorl_tests.log 2>&1; echo DONE_EXIT_$? >> /tmp/eorl_tests.log'

# poll from the host shell
docker exec devcontainer-frappe-1 tail -5 /tmp/eorl_tests.log
```

Done when the log ends with `DONE_EXIT_0` and the unittest summary reports 140 tests and `OK`.

One module only (**Verified** on the demo site on 2026-11-01 with the construct-registry and theory-compiler modules):

```bash
bench --site erpnext.localhost run-tests --module eorl_lab.eorl_lab.doctype.eorl_run.test_eorl_run
```

Known behaviour:

- The live-model test can fail once with `finish_reason="length"`. Run it again; a retry passed.
- Test files live next to their DocTypes under `eorl_lab/eorl_lab/doctype/`, 21 files in total.

Docs build (CI does this on every push to `main`): from the repo root run `python3 docs/gen_doctype_docs.py` and then `mkdocs build --strict`. Whether `mkdocs` is installed in the container right now is **Not tested**; `docs-requirements.txt` lists what it needs.

## 6. Before anything goes on the internet

Everything here applies to Option A and Option B. The status column is for the **demo site** (`eorl-demo.localhost`, port 8002), which is the only site that should ever be exposed.

| # | What | How | Status |
|---|---|---|---|
| 1 | Strong, unique `Administrator` password | Generated and set; stored in `~/eorl_live/credentials.env`. To change it: `read -rs PW; bench --site eorl-demo.localhost set-admin-password "$PW"; unset PW` | **Done**, 2026-11-01 |
| 2 | A reviewer account with only the **EORL Viewer** role | `reviewer@example.org`, System User, only EORL Viewer, no welcome email. EORL Viewer has read-only permission on the EORL DocTypes. A Module Profile that blocks the non-EORL modules would hide the rest of ERPNext from the reviewer (cosmetic, not a security control). | **Done**. The role was checked in the browser (section 3.4). Module Profile not applied. |
| 3 | Website signup disabled | Website Settings → Disable Signup | **Verified** on the demo site: `disable_signup` = 1, a guest `sign_up` call returns "Sign Up is disabled", and anonymous `list_runs` and `/api/resource/EORL Run` return 403. |
| 4 | Remove `allow_tests` from the site config | See below | **Done** on the demo site. |
| 5 | Rotate the vLLM API key and the GitHub token | Section 11. The vLLM key is no longer in the demo site's config, but it was pasted into a chat. | **Not done. Yours to do** |
| 6 | Serve one site only | The supervisor (section 3.4) runs single-site servers. Never expose `bench start` on 8000, where the other three sites answer to their own `Host` names. | By design |
| 7 | Expose a single port, never 8000-8005 or 9000-9005 | Funnel and the tunnel each publish one local port. Leave the compose `ports:` lines alone. Expose 8002 only, never 8001. | By design |
| 8 | Keep participant data out of the exposed site | `erpnext.localhost` holds the erp_research study data. The demo site was created clean, from nothing. | **Done** (section 3.4) |
| 9 | Close the five role gaps below | `frappe.only_for([...])` plus tests | **Not done.** Needs your go-ahead. |

Item 4. How to remove the key (done on the demo site), and how to put it back for a test run:

```bash
# inside the container, in the bench directory
python3 - <<'PY'
import json
p = "sites/eorl-demo.localhost/site_config.json"
c = json.load(open(p))
for k in ("allow_tests", "qwen_api_key", "qwen_base_url", "qwen_model"):
    c.pop(k, None)
json.dump(c, open(p, "w"), indent=1)
PY

# to run tests again
bench --site eorl-demo.localhost set-config allow_tests True --parse
```

Item 9, the role gaps. These five whitelisted functions do not call `frappe.only_for(...)`. They use `frappe.get_all`, which ignores DocType permissions, so **any logged-in user** can call them through `/api/method/...`:

| Function | Location |
|---|---|
| `list_runs` | `eorl_lab/api/runs.py:19` |
| `get_run_detail` | `eorl_lab/api/runs.py:33` |
| `list_episodes` | `eorl_lab/api/traces.py:5` |
| `get_episode_trace` | `eorl_lab/api/traces.py:15` |
| `compare_groups` | `eorl_lab/api/analysis.py:158` (also writes `EORL Analysis Result` rows) |

None has `allow_guest`, so a login is required. With signup disabled and a single reviewer account, the exposure is a reviewer reading run data and creating analysis rows. Adding `frappe.only_for([...])` with tests would close it. These five were the exceptions found when the API functions were audited; the others call `frappe.only_for`.

Behaviour of the dev server behind a TLS proxy (**Verified** with simulated proxy headers):

- Redirects use a relative `Location` (`/login?redirect-to=...`), so they survive an HTTPS front end.
- The `sid` session cookie is `HttpOnly; SameSite=Lax` and has no `Secure` flag, because the server sees plain HTTP. It still works over HTTPS.
- This is Werkzeug's development server, not a production server. It suits a handful of reviewers, not load.
- The site is up only while the lab machine is powered and the container is running. The supervisor (section 3.4) restarts a crashed server within five seconds and a cron `@reboot` entry should start it after a reboot, but the reboot path is **Not tested**. Check `status` after any reboot, and avoid rebooting the lab machine during the review window.

## 7. Option A: Tailscale Funnel

A stable HTTPS URL served through Tailscale's relays, with a certificate Tailscale manages.

**State today (Verified 2026-11-01, after the rename):** Funnel is on. `tailscale funnel status` shows `https://enterpriseailab.taile74753.ts.net` proxying `/` to `http://100.117.207.117:8002`, the demo site, so certificates and the Funnel attribute are enabled and the loopback forwarder (step A3) is not needed. Through the public URL `/api/method/ping` returns pong, `/login` returns 200, and the reviewer login and the new EORL endpoints work. The status also still lists a serve entry for the old name `https://agrim.taile74753.ts.net`; that name no longer resolves, so the entry is inert. Expose the demo site (port 8002), never the working site. Steps A1 to A4 below are the record of how to set this up.

**Step A1. Blocked on you, as tailnet owner.** In the Tailscale admin console:

1. DNS → HTTPS Certificates → enable.
2. Access controls → add a Funnel attribute to the policy file:

   ```json
   "nodeAttrs": [
     { "target": ["autogroup:member"], "attr": ["funnel"] }
   ]
   ```

   Running `tailscale funnel 8002` once may print a link that does both steps. **Not tested.**

**Step A2.** Check that the demo server is up: `~/eorl_live/eorl_live_ctl.sh status` should show pong on 8002 (section 3.4).

**Step A3.** Give Funnel a service on the lab machine's own loopback. `tailscale funnel` proxies to a service on the local machine, and Docker published port 8002 only on the tailnet IP. Run the small forwarder in [Appendix A](#appendix-a-loopback-forwarder) on the **host** shell. **Verified** on 2026-11-01 with the script set to port 8001: `curl http://127.0.0.1:8001/api/method/ping` on the lab machine returned pong and `/login` returned 200 through the forwarder. The script as written below uses 8002; that exact setting has **not been run**, though only the two port numbers differ.

Whether `tailscale funnel` would accept `http://100.117.207.117:8002` directly is **Not tested**; the forwarder removes the question. The alternative is adding `"127.0.0.1:8002:8002"` to the compose `ports:` list, which recreates the frappe container, so prefer the forwarder.

**Step A4.** On the host shell:

```bash
tailscale funnel --bg 8002
tailscale funnel status
```

Then open `https://enterpriseailab.taile74753.ts.net` from a device that is **not** on your tailnet (a phone on mobile data is enough) and log in once as the reviewer. **Not tested**, because A1 is blocked.

**Step A5, to take it down:**

```bash
tailscale funnel reset
pkill -f "[e]orl_fwd"
# the demo server keeps running for tailnet use; stop it with the supervisor (section 3.4) if you want it down
```

Trade-offs:

- The URL is stable across restarts, which suits a link in a submission form.
- Since the rename the URL no longer contains `agrim`; it contains the tailnet name `taile74753` only. See section 10.
- The rename changed the SSH target to `agrim@enterpriseailab` and dropped the old URL.
- Tailscale's relays carry the traffic, and the tailnet owner controls Funnel. It stops when you run `tailscale funnel reset`.

## 8. Option B: Cloudflare quick tunnel

No account, no tailnet admin step, and the URL does not contain your name.

**Not tested.** `cloudflared` is not installed on the lab machine or in the container, and nothing was downloaded.

The tunnel starts from inside the container and points at the local server, so it needs no Docker port publishing and no forwarder:

```bash
# inside the container (x86_64, curl is installed)
mkdir -p ~/bin
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/bin/cloudflared
chmod +x ~/bin/cloudflared

# the demo server must already be running on port 8002 (section 3.4)
~/bin/cloudflared tunnel --url http://localhost:8002
```

It prints a URL of the form `https://<random-words>.trycloudflare.com`. Open it from a device off your tailnet and log in once as the reviewer.

Trade-offs:

- The URL is different every time the tunnel starts, so it cannot go into a PDF in advance. Put it in the submission form or a reviewer note once it is live, and update it if you restart.
- Quick tunnels come with no uptime guarantee and are meant for testing.
- `~/bin` is in the container's own layer and is lost if the container is recreated. Download it again if so.
- A stable address needs a Cloudflare account and a domain (a named tunnel). That is out of scope here.

Stop it with Ctrl-C, or `pkill -f "[c]loudflared tunnel"`.

## 9. Option C: no live instance

Nothing running, so nothing to keep up and nothing new exposed:

- Reviewer access to the private repo (add them as collaborators) or a public repo after a secrets scan.
- A 2 to 3 minute screen recording of the Scientific Cockpit and Process Explorer.
- Figure 7 of the technical appendix, which is made of real screenshots from this system.
- The docs site, if you decide it is acceptable (section 10).

The proposal and appendix both say the repo link and reviewer access are "provided in the submission form", so any option works with the text as written.

A sensible combination is Option C as the baseline, plus Option A or B switched on only for the review window and switched off afterwards.

## 10. Anonymity

If the review is blind, these surfaces identify you:

| Surface | What it shows |
|---|---|
| Funnel URL | `enterpriseailab.taile74753.ts.net`: no personal name since the 2026-11-01 rename |
| Docs site `https://agrimsachdeva.github.io/eorl_lab/` | Your GitHub username. It is **public even though the repo is private**. |
| Repo URL | Your GitHub username |
| Git history | Commit author `agrim <agrim@arizona.edu>` on every commit, visible to anyone with repo access |
| Cloudflare quick tunnel | Nothing |

The demo site's `EORL Model Profile` named "Qwen3 27B (vLLM)" has a `base_url` that is the vLLM host's tailnet address. Since the submission-day build `base_url` and `api_key_reference` are at permission level 1, which the EORL Viewer role cannot read, and model events record the profile name rather than the address. Note that the reviewer account on the demo site currently also holds EORL Researcher, which can read level 1. **Verified** 2026-11-01: the run records themselves (`provider_snapshots_json`, `agent_snapshots_json` and the other snapshot fields of RUN-00013 and RUN-00014) do not contain an address. The address is private to the tailnet and the API key is not stored there, but it is an internal detail. Either clear the profile's `base_url` before a public review (live runs then stop working until it is put back) or accept it.

The change log that came with the revised Word files already lists the author block, the docs site and the repo link as items for you to settle. Nothing here has been changed.

## 11. Credentials

Two secrets were pasted into the chat during this project. Treat both as compromised.

- **GitHub personal access token.** Revoke it in GitHub → Settings → Developer settings → Personal access tokens, then use a new one or an SSH key stored on the lab machine only.
- **vLLM API key.** Rotate it on the vLLM host before any public exposure. The new key belongs in `sites/erpnext.localhost/site_config.json` as `qwen_api_key`, or in an environment variable on the lab machine. Never in a DocType field, a commit, or a document like this one.

Neither secret was written to disk or to git config by Claude, and neither appears in this file.

The demo site's generated passwords (Administrator and the reviewer) are in `~/eorl_live/credentials.env` on the lab machine, mode 600. This file records the path only. Read it on the lab machine, or pass the reviewer password to the person who needs it through a channel other than this repo.

## 12. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `tailscale ssh` prints a login URL | Re-approval needed. Open the link in a browser. |
| Connection refused on 8000, 8001 or 8002 | The container is up but no web server is running. `~/eorl_live/eorl_live_ctl.sh status`, then `start` (section 3.4). |
| Port already in use | An old bench process. `ps aux | grep "[b]ench"` inside the container, then stop it. |
| Page says the site does not exist on port 8000 | The `Host` header is not `erpnext.localhost`. Use section 4.1. |
| Browser ignores the hosts-file entry | See the note in section 4.2. Use section 4.1. |
| Test suite hangs or reports a lock wait | Another bench process was running. Stop it and rerun. |
| Live-model test fails with `finish_reason="length"` | Rerun that test; it passes on retry. |
| A live episode fails with `finish_reason='length'` | The model profile has no `max_tokens`, so the provider falls back to 600 and Qwen spends it on reasoning. Set `max_tokens` to 4096 on the profile. RUN-00013 on the demo site is the kept record of this failure. |
| A new site has no constructs (tests error on a missing EORL Construct) | `bench install-app` marks every patch as already run. Before 2026-11-01 a fresh site never got the seed. The `after_install` hook in `eorl_lab/install.py` now seeds them; on an older site run `eorl_lab.patches.v1_seed_initial_constructs.execute`. |
| After a reboot nothing loads | Containers restart on their own. The cron `@reboot` entry should start the servers; if it did not, run `~/eorl_live/eorl_live_ctl.sh start` and read `~/eorl_live/boot.log`. Check `tailscale status` too. |
| `tailscale funnel` says Funnel is not enabled | Section 7, step A1. |

## 13. Decisions and open items

1. Resolved 2026-11-01: the demo site is public through Funnel. Switch it off after the review window with `tailscale funnel reset`.
2. Resolved 2026-11-01: Funnel at `https://enterpriseailab.taile74753.ts.net`, with no personal name in the URL.
3. Done 2026-11-01: role checks added to every whitelisted read function, with tests. Remove `EORL Researcher` from the reviewer account so the account is read-only.
4. Rotate the GitHub token and the vLLM key (section 11) before any public request.
5. Decide what to do about the vLLM address in the model profile (section 10): leave it, or clear it for the review window.
6. Decide whether to apply a Module Profile to the reviewer account (section 6 item 2). It hides the rest of ERPNext. It is not a security control.
7. Decide whether the public docs site and the git author identity are acceptable under blind review (section 10).
8. Run the full 140-test suite once on the demo site with the install fix. The first run passed 134; the two modules that held the other six passed on re-run (15 and 5 tests), but no single full run has been made on the fixed code.
9. Reboot check. After the next reboot of the lab machine, run `~/eorl_live/eorl_live_ctl.sh status` and read `~/eorl_live/boot.log`.
10. Not tested in a browser on the demo site: the Power Planner, Survival Analysis, Robustness Diagnostics, Paired-Branch Inference and Theory Compiler pages, and any browser other than Chrome.
11. Authorize the claude.ai Gmail, Google Calendar and Scholar Gateway connectors in your claude.ai connector settings if you want them used in future sessions.

## Appendix A: loopback forwarder

Listens on the lab machine's `127.0.0.1:8002` and relays to `100.117.207.117:8002` (the demo site), so a tool that wants a local service (Funnel) finds one. Loopback only, so nothing new is reachable from the network. **Verified** 2026-11-01 with ports set to 8001; the 8002 setting is untested.

Save it on the host (not in the container) as `/tmp/eorl_fwd.py`:

```python
import asyncio

LISTEN_HOST, LISTEN_PORT = "127.0.0.1", 8002
TARGET_HOST, TARGET_PORT = "100.117.207.117", 8002


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


async def handle(client_r, client_w):
    try:
        up_r, up_w = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    except OSError:
        client_w.close()
        return
    await asyncio.gather(pipe(client_r, up_w), pipe(up_r, client_w))


async def main():
    server = await asyncio.start_server(handle, LISTEN_HOST, LISTEN_PORT)
    print(f"forwarding {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}", flush=True)
    async with server:
        await server.serve_forever()


asyncio.run(main())
```

Run and stop it:

```bash
nohup python3 /tmp/eorl_fwd.py > /tmp/eorl_fwd.log 2>&1 &
pkill -f "[e]orl_fwd"
```

If you want it to survive a reboot, it needs a systemd unit, which needs `sudo` (a password on the lab machine). It is not set up.
