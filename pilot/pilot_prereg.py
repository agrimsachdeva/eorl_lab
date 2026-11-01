import frappe

frappe.init(site="eorl-demo.localhost", sites_path="/workspace/development/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

EXP = "Pilot P1: Specialist Handoff vs Broad Autonomy (Qwen3, stable)"
HYP = """Registered before the first pilot run. Fixed design: 8 paired seeds (7100-7107) x 2 architectures x 6 episodes, no interim analysis.

H1 (P1, concentration). Across independent runs under stable conditions, broad autonomy yields a higher modal-path share and a lower sequence entropy than specialist handoff (two-sided tests, alpha .05).
H1-check (manipulation check). Actor continuity is higher under broad autonomy. This holds by construction in broad autonomy and is reported only to confirm the manipulation.
H0 (rival, constraint dominance). The architectures differ by less than one deviating episode per run on both primary measures. Bounds, declared here: modal-path share +/-0.17 (one deviating episode of six) and sequence entropy +/-0.65 bits (entropy of a run with one deviating episode of six), tested by two one-sided tests.

Primary outcomes: modal_path_share, sequence_entropy (run level). Inference: Welch t and permutation test (10,000), Hedges g with 95% CI, TOST with the bounds above. Two primary tests, no multiplicity correction; both are reported.
Descriptive only (no inference): strict completion (purchase order, receipt, invoice and payment entry all submitted), tool calls per episode, quality exceptions and how they were handled, episodes per run, run failures.
Exclusions: a run lost to an infrastructure error (endpoint unreachable, timeout) is re-run once with the same seed. Model-side failures (malformed tool call, token limit, tool denial) are kept and counted.
Interpretation rule: equivalence on both measures is reported as consistent with constraint dominance in this routine; failure of both equivalence tests with no significant difference is reported as inconclusive.
Not tested in this pilot: P2 (memory conditions are not run) and P3 (no supplier-quality shock exists)."""

if not frappe.db.exists("EORL Experiment", EXP):
    frappe.get_doc({
        "doctype": "EORL Experiment", "experiment_name": EXP, "status": "validated",
        "research_question": "Under stable conditions, does giving one language-model actor authority over the whole procure-to-pay chain concentrate performances in fewer process paths than four role-bounded specialists?",
        "theoretical_mechanism": "Broader autonomy raises actor continuity, which should concentrate performances in fewer paths (P1). Document dependencies in the ERP system may fix the path regardless of architecture (constraint dominance).",
        "focal_construct": "Routine coherence",
        "primary_outcomes": "modal_path_share; sequence_entropy",
        "pre_registered_hypotheses": HYP,
        "architecture_a": "Pilot Specialist Handoff (Qwen3)", "architecture_b": "Pilot Broad Autonomy (Qwen3)",
        "episode_count": 6, "repetitions_per_cell": 8, "seed_strategy": "paired", "base_seed": 7100,
        "model_replication_strategy": "None in this pilot: one model (Qwen3 27B AWQ), sampling temperature 0.6, top-p 0.95, thinking on.",
        "stopping_rules": "Fixed n; no interim analysis; arm order alternates by repetition.",
    }).insert(ignore_permissions=True)
    print("created experiment")

PLANS = [
    ("Pilot P1: modal path share", "modal_path_share", "-0.17,0.17", "Difference in run-level modal-path share, specialist minus broad"),
    ("Pilot P1: sequence entropy", "sequence_entropy", "-0.65,0.65", "Difference in run-level sequence entropy (bits), specialist minus broad"),
    ("Pilot check: actor continuity", "actor_continuity", None, "Difference in actor continuity, specialist minus broad (manipulation check)"),
]
for name, metric, bounds, estimand in PLANS:
    if frappe.db.exists("EORL Analysis Plan", name):
        print("exists", name); continue
    frappe.get_doc({
        "doctype": "EORL Analysis Plan", "plan_name": name, "version": "1.0", "experiment": EXP,
        "research_question": "P1-lite", "estimand": estimand, "outcome_metric": metric,
        "contrast": "specialist handoff vs broad autonomy", "analysis_unit": "run", "model_family": "welch_t",
        "multiple_testing_family": "pilot primary (two tests, uncorrected)" if bounds else "manipulation check",
        "alpha": 0.05, "permutation_iterations": 10000, "equivalence_bounds": bounds,
        "exclusion_rule": "Re-run infrastructure errors once with the same seed; keep model-side failures.",
    }).insert(ignore_permissions=True)
    print("created plan", name)
frappe.db.commit()
print("modified:", frappe.db.get_value("EORL Experiment", EXP, "creation"))
frappe.destroy()
