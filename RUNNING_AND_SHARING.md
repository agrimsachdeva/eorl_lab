# Running, testing and sharing EORL Lab

How to start the EORL Lab app on agrim, run its tests, look at it from another machine, and (if you decide to) put a live copy on the internet for the *Organization Science* submission.

> **Operator document.** It contains this machine's tailnet IP address and hostname. It is deliberately **not** in `docs/` and **not** in the `mkdocs.yml` nav, because the public docs site is built from those. Read it through before you give anyone access to the repository.

Last updated: 2026-11-01.

How to read the status labels:

| Label | Meaning |
|---|---|
| **Verified** | Run on agrim (or against it over the tailnet) on 2026-11-01 and the result was as described. |
| **Not tested** | Written from `--help` output, source code or vendor documentation. Nothing was run. Try it once before you rely on it. |
| **Blocked** | Needs something only you (the tailnet owner) can do. |

## Contents

1. [Facts you need](#1-facts-you-need)
2. [Reach agrim](#2-reach-agrim)
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
| Machine | `agrim`, Ubuntu, Tailscale IPv4 `100.117.207.117`, tailnet `agrimsachdeva.github`, MagicDNS name `agrim.taile74753.ts.net`, Tailscale 1.104.2 |
| Repo (host path) | `~/frappe_docker/development/frappe-bench/apps/eorl_lab` |
| Repo (container path) | `/workspace/development/frappe-bench/apps/eorl_lab` |
| Git | remote `upstream`, branch `main`. Run git on the **host** shell, not in the container. |
| Compose file | `~/frappe_docker/.devcontainer/docker-compose.yml`, compose project name `devcontainer` |
| Containers | `devcontainer-frappe-1`, `devcontainer-mariadb-1`, `devcontainer-redis-cache-1`, `devcontainer-redis-queue-1`. All have `restart: unless-stopped`, so they come back after a reboot. |
| Bench | `/workspace/development/frappe-bench` in the container, virtualenv `env`, Python 3.10.12 |
| Versions | Frappe 14.101.1, ERPNext 14.92.14 |
| EORL site | `erpnext.localhost` |
| Other sites on the bench | `agentic.localhost`, `auto.localhost`, `conversational.localhost` (not used by EORL) |
| Published ports | 8000-8005 and 9000-9005, bound to the **tailnet IP only** (compose lines 55-57). They are not reachable on `localhost` of agrim and not on the LAN. |
| Web server | **Not started automatically.** The container command is `sleep infinity`, so a running container does not mean a running site. |

Frappe picks the site from the HTTP `Host` header. That is why section 4 has two routes.

## 2. Reach agrim

```bash
tailscale ssh agrim@agrim
```

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

## 4. Open it in a browser

### 4.1 From any machine on your tailnet (recommended)

1. Run section 3.3 on agrim.
2. On the other machine (signed in to the same tailnet) open `http://100.117.207.117:8001/`.
3. Log in as `Administrator` with the password you set, or as a reviewer account (section 6, item 2).
4. The EORL workspace is at `/app/eorl-lab` and links to every page.

**Verified** with `curl` from the Jetstream VM: ping, the login page and the unauthenticated redirect (section 3.3). A full interactive browser login through port 8001 has not been done yet, so do one before you depend on it.

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

- `allow_tests` is set in the site config (it is today). Section 6 item 4 removes it for public exposure, so put it back first.
- The vLLM host named in the site config (`qwen_base_url`) is reachable. One test calls the live model.
- No other `bench` process is running. A second bench process during the suite caused a MySQL naming-series deadlock in SOTA Milestone 8.
- Frappe's runner works against the `erpnext.localhost` database itself. Do not run it while someone is using the site.

```bash
# inside the container, in the bench directory, venv active
bench --site erpnext.localhost run-tests --app eorl_lab
```

Expect about 5 minutes and 140 tests (the count at SOTA Milestone 10).

Detached form, for when you are connected over SSH and do not want a dropped connection to kill it:

```bash
docker exec -d -w /workspace/development/frappe-bench devcontainer-frappe-1 bash -c \
  'source env/bin/activate && bench --site erpnext.localhost run-tests --app eorl_lab > /tmp/eorl_tests.log 2>&1; echo DONE_EXIT_$? >> /tmp/eorl_tests.log'

# poll from the host shell
docker exec devcontainer-frappe-1 tail -5 /tmp/eorl_tests.log
```

Done when the log ends with `DONE_EXIT_0` and the unittest summary reports 140 tests and `OK`.

One module only (path form follows the test tree; **Not tested** today):

```bash
bench --site erpnext.localhost run-tests --module eorl_lab.eorl_lab.doctype.eorl_run.test_eorl_run
```

Known behaviour:

- The live-model test can fail once with `finish_reason="length"`. Run it again; a retry passed.
- Test files live next to their DocTypes under `eorl_lab/eorl_lab/doctype/`, 21 files in total.

Docs build (CI does this on every push to `main`): from the repo root run `python3 docs/gen_doctype_docs.py` and then `mkdocs build --strict`. Whether `mkdocs` is installed in the container right now is **Not tested**; `docs-requirements.txt` lists what it needs.

## 6. Before anything goes on the internet

Everything here applies to Option A and Option B. None of it has been applied except where the status says so.

| # | What | How | Status |
|---|---|---|---|
| 1 | Strong, unique `Administrator` password | `read -rs PW; bench --site erpnext.localhost set-admin-password "$PW"; unset PW` (keeps the password out of shell history) | Not done. Syntax per Frappe 14, **Not tested**. |
| 2 | A reviewer account with only the **EORL Viewer** role | Desk → User → Add User. Give it only EORL Viewer. In a Module Profile, block the non-EORL modules so the reviewer does not see the rest of ERPNext (cosmetic, not a security control). EORL Viewer has read-only permission on the EORL DocTypes. | Not done |
| 3 | Website signup disabled | Website Settings → Disable Signup | **Verified**: already set (`disable_signup` = 1 on 2026-11-01) |
| 4 | Remove `allow_tests` from the site config | See below | Not done. The edit was **Verified** on a copy. |
| 5 | Rotate the vLLM API key and the GitHub token | Section 11 | Not done |
| 6 | Serve one site only | Use section 3.3 (port 8001). Never expose `bench start` on 8000, where the other three sites answer to their own `Host` names. | Procedure verified |
| 7 | Expose a single port, never 8000-8005 or 9000-9005 | Funnel and the tunnel each publish one local port. Leave the compose `ports:` lines alone. | By design |
| 8 | Check what is in the site | `erpnext.localhost` is an ERPNext site. Look at what other records it holds before reviewers can reach it. | Not done |

Item 4. Remove the key, then restore it before the next test run:

```bash
# inside the container, in the bench directory
python3 - <<'PY'
import json
p = "sites/erpnext.localhost/site_config.json"
c = json.load(open(p))
c.pop("allow_tests", None)
json.dump(c, open(p, "w"), indent=1)
PY

# to run tests again
bench --site erpnext.localhost set-config allow_tests True --parse
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
- The site is up only while agrim is powered, the container is running and you have started the server. Nothing restarts it. Do not reboot agrim during the review window.

## 7. Option A: Tailscale Funnel

A stable HTTPS URL served through Tailscale's relays, with a certificate Tailscale manages.

**State today (Verified):** `tailscale funnel status` says "No serve config". HTTPS certificates are not enabled for the tailnet (no cert domains) and the Funnel node attribute is missing. The URL would be `https://agrim.taile74753.ts.net`.

**Step A1. Blocked on you, as tailnet owner.** In the Tailscale admin console:

1. DNS → HTTPS Certificates → enable.
2. Access controls → add a Funnel attribute to the policy file:

   ```json
   "nodeAttrs": [
     { "target": ["autogroup:member"], "attr": ["funnel"] }
   ]
   ```

   Running `tailscale funnel 8001` once may print a link that does both steps. **Not tested.**

**Step A2.** Start the single-site server (section 3.3).

**Step A3.** Give Funnel a service on agrim's own loopback. `tailscale funnel` proxies to a service on the local machine, and Docker published port 8001 only on the tailnet IP. Run the small forwarder in [Appendix A](#appendix-a-loopback-forwarder) on the **host** shell. **Verified** on 2026-11-01: with the server up, `curl http://127.0.0.1:8001/api/method/ping` on agrim returned pong and `/login` returned 200 through the forwarder.

Whether `tailscale funnel` would accept `http://100.117.207.117:8001` directly is **Not tested**; the forwarder removes the question. The alternative is adding `"127.0.0.1:8001:8001"` to the compose `ports:` list, which recreates the frappe container, so prefer the forwarder.

**Step A4.** On the host shell:

```bash
tailscale funnel --bg 8001
tailscale funnel status
```

Then open `https://agrim.taile74753.ts.net` from a device that is **not** on your tailnet (a phone on mobile data is enough) and log in once as the reviewer. **Not tested**, because A1 is blocked.

**Step A5, to take it down:**

```bash
tailscale funnel reset
pkill -f "[e]orl_fwd"
# and stop the server inside the container (section 3.3)
```

Trade-offs:

- The URL is stable across restarts, which suits a link in a submission form.
- It contains `agrim`. See section 10.
- Renaming the machine in the admin console would change the URL, but it would also break `tailscale ssh agrim@agrim` and anything else that uses that name.
- Tailscale's relays carry the traffic, and the tailnet owner controls Funnel. It stops when you run `tailscale funnel reset`.

## 8. Option B: Cloudflare quick tunnel

No account, no tailnet admin step, and the URL does not contain your name.

**Not tested.** `cloudflared` is not installed on agrim or in the container, and nothing was downloaded.

The tunnel starts from inside the container and points at the local server, so it needs no Docker port publishing and no forwarder:

```bash
# inside the container (x86_64, curl is installed)
mkdir -p ~/bin
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/bin/cloudflared
chmod +x ~/bin/cloudflared

# section 3.3 must already be running on port 8001
~/bin/cloudflared tunnel --url http://localhost:8001
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
| Funnel URL | `agrim` in the hostname |
| Docs site `https://agrimsachdeva.github.io/eorl_lab/` | Your GitHub username. It is **public even though the repo is private**. |
| Repo URL | Your GitHub username |
| Git history | Commit author `agrim <agrim@arizona.edu>` on every commit, visible to anyone with repo access |
| Cloudflare quick tunnel | Nothing |

The change log that came with the revised Word files already lists the author block, the docs site and the repo link as items for you to settle. Nothing here has been changed.

## 11. Credentials

Two secrets were pasted into the chat during this project. Treat both as compromised.

- **GitHub personal access token.** Revoke it in GitHub → Settings → Developer settings → Personal access tokens, then use a new one or an SSH key stored on agrim only.
- **vLLM API key.** Rotate it on the vLLM host before any public exposure. The new key belongs in `sites/erpnext.localhost/site_config.json` as `qwen_api_key`, or in an environment variable on agrim. Never in a DocType field, a commit, or a document like this one.

Neither secret was written to disk or to git config by Claude, and neither appears in this file.

## 12. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `tailscale ssh` prints a login URL | Re-approval needed. Open the link in a browser. |
| Connection refused on 8000 or 8001 | The container is up but no web server is running. Start one (section 3). |
| Port already in use | An old bench process. `ps aux | grep "[b]ench"` inside the container, then stop it. |
| Page says the site does not exist on port 8000 | The `Host` header is not `erpnext.localhost`. Use section 4.1. |
| Browser ignores the hosts-file entry | See the note in section 4.2. Use section 4.1. |
| Test suite hangs or reports a lock wait | Another bench process was running. Stop it and rerun. |
| Live-model test fails with `finish_reason="length"` | Rerun that test; it passes on retry. |
| After a reboot nothing loads | Containers restart on their own, the web server does not. Start it again. Check `tailscale status` too. |
| `tailscale funnel` says Funnel is not enabled | Section 7, step A1. |

## 13. Decisions and open items

1. Is a live instance worth having at all, or is Option C enough for the Stage 1 submission?
2. If yes: Funnel (stable, but `agrim` in the URL, and needs you to enable it in the admin console) or Cloudflare (anonymous, URL changes)?
3. Close the five role gaps in section 6 item 9, with tests. Say so and it can be done.
4. Apply section 6 items 1, 2, 4 and 5 before the first public request.
5. Rotate the GitHub token and the vLLM key (section 11).
6. Decide whether the public docs site and the git author identity are acceptable under blind review (section 10).
7. Authorize the claude.ai Gmail, Google Calendar and Scholar Gateway connectors in your claude.ai connector settings if you want them used in future sessions.

## Appendix A: loopback forwarder

Listens on agrim's `127.0.0.1:8001` and relays to `100.117.207.117:8001`, so a tool that wants a local service (Funnel) finds one. Loopback only, so nothing new is reachable from the network. **Verified** 2026-11-01.

Save it on the host (not in the container) as `/tmp/eorl_fwd.py`:

```python
import asyncio

LISTEN_HOST, LISTEN_PORT = "127.0.0.1", 8001
TARGET_HOST, TARGET_PORT = "100.117.207.117", 8001


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

If you want it to survive a reboot, it needs a systemd unit, which needs `sudo` (a password on agrim). It is not set up.
