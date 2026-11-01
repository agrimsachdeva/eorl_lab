"""Pilot analysis. Usage: python pilot_analyze.py [--full] [RUN ...]
Without --full: read-only descriptive statistics (safe while a pilot is running).
With --full: compute run metrics and the pre-registered comparisons (writes Metric and Analysis Result rows).
Runs are taken from pilot_logs/state.json unless RUN names are given (treated as ungrouped)."""
import json, os, sys, collections, statistics
import frappe

LOGDIR = "/workspace/development/frappe-bench/pilot_logs"
FULL = "--full" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]

frappe.init(site="eorl-demo.localhost", sites_path="/workspace/development/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

state = json.load(open(os.path.join(LOGDIR, "state.json"))) if os.path.exists(os.path.join(LOGDIR, "state.json")) else {}
groups = {"specialist": [], "broad": []}
for key, v in sorted(state.items(), key=lambda kv: (int(kv[0].split(":")[0]), kv[0])):
    if v.get("status") == "done":
        groups[v["arm"]].append(v["run"])
if args:
    groups = {"adhoc": args}

SUBMITS = ["purchase_order_submitted", "purchase_receipt_submitted", "purchase_invoice_submitted", "payment_entry_submitted"]


def episode_rows(run):
    rows = []
    eps = frappe.get_all("EORL Episode", filters={"run": run}, fields=["name", "episode_number", "status", "success", "outcome_json"],
                         order_by="episode_number asc")
    for ep in eps:
        evs = frappe.get_all("EORL Event", filters={"run": run, "episode": ep.name, "event_type": "tool_result"},
                             fields=["target_id", "actor_slot", "success"], order_by="sequence_no asc")
        seq = [e.target_id for e in evs if e.target_id != "finish_turn"]
        out = frappe.parse_json(ep.outcome_json or "{}")
        scratch = {}
        for stage in (out.get("stage_results") or {}).values():
            scratch.update(stage or {})
        denied = frappe.db.count("EORL Event", {"run": run, "episode": ep.name, "event_type": "tool_denied"})
        rows.append({
            "run": run, "episode": ep.episode_number, "status": ep.status, "stored_success": bool(ep.success),
            "strict_complete": all(scratch.get(k) for k in SUBMITS),
            "quality_passed": out.get("quality_passed"), "supplier": scratch.get("supplier"),
            "path": seq, "n_calls": len(evs), "n_denied": denied, "failure_reason": out.get("failure_reason"),
            "escalated": "escalate_quality_exception" in seq,
        })
    return rows


report = {"groups": {}, "runs": {}}
for g, runs in groups.items():
    rows = []
    for r in runs:
        er = episode_rows(r)
        report["runs"][r] = er
        rows += er
    n = len(rows)
    if not n:
        report["groups"][g] = {"runs": len(runs), "episodes": 0}; continue
    paths = collections.Counter(tuple(r["path"]) for r in rows)
    modal, modal_n = paths.most_common(1)[0]
    sup = collections.Counter(r["supplier"] for r in rows)
    ep_per_run = [len(report["runs"][r]) for r in runs]
    report["groups"][g] = {
        "runs": len(runs), "episodes": n, "episodes_per_run_mean": round(statistics.mean(ep_per_run), 2),
        "runs_not_6_episodes": sum(1 for x in ep_per_run if x < 6),
        "stored_success_rate": round(sum(r["stored_success"] for r in rows) / n, 3),
        "strict_complete_rate": round(sum(r["strict_complete"] for r in rows) / n, 3),
        "distinct_paths": len(paths), "modal_path_episodes": modal_n, "modal_path": list(modal),
        "episodes_off_modal_path": n - modal_n,
        "calls_per_episode_mean": round(statistics.mean(r["n_calls"] for r in rows), 2),
        "calls_per_episode_sd": round(statistics.pstdev(r["n_calls"] for r in rows), 2),
        "quality_failed_episodes": sum(1 for r in rows if r["quality_passed"] is False),
        "escalated_episodes": sum(1 for r in rows if r["escalated"]),
        "tool_denials": sum(r["n_denied"] for r in rows),
        "supplier_choice": dict(sup),
        "failures": [(r["run"], r["episode"], (r["failure_reason"] or "")[:160]) for r in rows if not r["stored_success"]],
        "other_paths": [{"path": list(p), "episodes": c} for p, c in paths.most_common()[1:]],
    }

if FULL and set(groups) == {"specialist", "broad"}:
    from eorl_lab.api.metrics import compute_run_metrics
    from eorl_lab.api.analysis import compare_groups
    per_run = {}
    for g, runs in groups.items():
        for r in runs:
            m = compute_run_metrics(r)["metrics"]
            per_run[r] = {k: m[k] for k in ("modal_path_share", "sequence_entropy", "unique_sequence_count", "actor_continuity", "success_rate")}
    frappe.db.commit()
    report["run_metrics"] = per_run
    report["comparisons"] = {}
    for plan in ("Pilot P1: modal path share", "Pilot P1: sequence entropy", "Pilot check: actor continuity"):
        try:
            res = compare_groups(plan, groups["specialist"], groups["broad"])
            report["comparisons"][plan] = {k: res.get(k) for k in ("n_independent_runs_a", "n_independent_runs_b", "n_episodes_a", "n_episodes_b", "mean_a", "mean_b", "standardized_effect", "results", "analysis_result_names")}
        except Exception as exc:
            frappe.db.rollback()
            metric = {"Pilot P1: modal path share": "modal_path_share", "Pilot P1: sequence entropy": "sequence_entropy", "Pilot check: actor continuity": "actor_continuity"}[plan]
            va = [per_run[r][metric] for r in groups["specialist"]]
            vb = [per_run[r][metric] for r in groups["broad"]]
            report["comparisons"][plan] = {"error": "%s: %s" % (type(exc).__name__, exc), "values_specialist": va, "values_broad": vb}
    frappe.db.commit()

out = os.path.join(LOGDIR, "results_full.json" if FULL else "results_descriptive.json")
json.dump(report, open(out, "w"), indent=1, default=str)
print(json.dumps(report["groups"], indent=1, default=str))
if FULL and "comparisons" in report:
    print(json.dumps(report["comparisons"], indent=1, default=str))
print("wrote", out)
frappe.destroy()
