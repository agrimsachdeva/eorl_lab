import json, sys, time
import frappe

frappe.init(site="eorl-demo.localhost", sites_path="/workspace/development/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")
from eorl_lab.runtime.orchestrator import run_architecture

ARCHS = ["Pilot Broad Autonomy (Qwen3)", "Pilot Specialist Handoff (Qwen3)"]
for arch in ARCHS:
    t0 = time.time()
    print("START", arch, flush=True)
    res = run_architecture(arch, seed=9001, episode_count=1)
    dt = time.time() - t0
    frappe.db.commit()
    evs = frappe.get_all("EORL Event", filters={"run": res["run"], "event_type": "tool_result"},
                         fields=["target_id", "actor_slot", "success"], order_by="creation asc, name asc")
    errs = frappe.get_all("EORL Event", filters={"run": res["run"], "event_type": "error"}, fields=["payload_json"])
    print("DONE", arch, "run", res["run"], "elapsed_s", round(dt, 1), "success", res["outcome"].get("success"),
          "quality_passed", res["outcome"].get("quality_passed"), "events", res["event_count"], flush=True)
    print("  path:", " > ".join(f"{e.actor_slot[:4]}:{e.target_id}{'' if e.success else '(X)'}" for e in evs), flush=True)
    print("  outcome keys:", {k: res["outcome"].get(k) for k in ("purchase_order","purchase_receipt","purchase_invoice","payment_entry","failure_reason")}, flush=True)
    for e in errs: print("  ERROR:", e.payload_json[:300], flush=True)
print("SMOKE_DONE", flush=True)
frappe.destroy()
