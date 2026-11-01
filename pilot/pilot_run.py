"""P1-lite pilot runner: paired seeds, interleaved arms, resumable.
Usage (inside the bench container, cwd = sites/):  python pilot_run.py REPS EPISODES BASE_SEED
"""
import json, os, sys, time, traceback
import frappe

REPS = int(sys.argv[1]); EPISODES = int(sys.argv[2]); BASE_SEED = int(sys.argv[3])
ARMS = {"specialist": "Pilot Specialist Handoff (Qwen3)", "broad": "Pilot Broad Autonomy (Qwen3)"}
LOGDIR = "/workspace/development/frappe-bench/pilot_logs"
os.makedirs(LOGDIR, exist_ok=True)
STATE = os.path.join(LOGDIR, "state.json")
state = json.load(open(STATE)) if os.path.exists(STATE) else {}

def log(msg):
    line = time.strftime("%H:%M:%S ", time.gmtime()) + msg
    print(line, flush=True)
    open(os.path.join(LOGDIR, "pilot.log"), "a").write(line + "\n")

frappe.init(site="eorl-demo.localhost", sites_path="/workspace/development/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
from eorl_lab.runtime.orchestrator import run_architecture

log(f"pilot start reps={REPS} episodes={EPISODES} base_seed={BASE_SEED}")
for rep in range(REPS):
    order = ["specialist", "broad"] if rep % 2 == 0 else ["broad", "specialist"]
    seed = BASE_SEED + rep
    for arm in order:
        key = f"{rep}:{arm}"
        if state.get(key, {}).get("status") == "done":
            continue
        t0 = time.time()
        log(f"START rep={rep} arm={arm} seed={seed}")
        try:
            res = run_architecture(ARMS[arm], seed=seed, episode_count=EPISODES)
            frappe.db.commit()
            state[key] = {"status": "done", "run": res["run"], "seed": seed, "arm": arm, "rep": rep,
                          "elapsed_s": round(time.time() - t0, 1),
                          "episodes_completed": len(res["episodes"]), "last_success": res["outcome"].get("success")}
            log(f"DONE rep={rep} arm={arm} run={res['run']} episodes={len(res['episodes'])} "
                f"last_success={res['outcome'].get('success')} elapsed={state[key]['elapsed_s']}s")
        except Exception:
            frappe.db.rollback()
            state[key] = {"status": "error", "seed": seed, "arm": arm, "rep": rep}
            log(f"ERROR rep={rep} arm={arm}\n" + traceback.format_exc())
        json.dump(state, open(STATE, "w"), indent=1)
log("PILOT_COMPLETE")
frappe.destroy()
