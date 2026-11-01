import json
import os

import frappe

from eorl_lab.api import analysis as analysis_api
from eorl_lab.api import experiments as experiments_api
from eorl_lab.api import metrics as metrics_api
from eorl_lab.api import runs as runs_api
from eorl_lab.runtime.orchestrator import run_architecture

SPECIALIST = {
	"purchasing_agent": ("Purchasing Agent", dict(may_submit_documents=0), ["get_supplier_options", "create_purchase_order"]),
	"purchasing_manager_agent": (
		"Purchasing Manager Agent", dict(may_submit_documents=1, may_approve=1), ["get_purchase_order", "submit_purchase_order"],
	),
	"warehouse_agent": (
		"Warehouse Agent", dict(may_submit_documents=1, may_message_agents=1),
		["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt", "inspect_received_goods", "escalate_quality_exception", "message_agent"],
	),
	"accounts_payable_agent": (
		"Accounts Payable Agent", dict(may_submit_documents=1),
		["get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice", "create_payment_entry", "submit_payment_entry"],
	),
}
BROAD_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status", "create_purchase_order", "submit_purchase_order",
	"create_purchase_receipt", "submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry", "inspect_received_goods", "escalate_quality_exception", "message_agent",
]


def _ins(doc):
	return frappe.get_doc(doc).insert(ignore_if_duplicate=True)


def seed_config():
	profile = _ins({"doctype": "EORL Model Profile", "profile_name": "Scripted Policy", "provider": "deterministic", "enabled": 1})
	slots = []
	for key, (label, flags, tools) in SPECIALIST.items():
		policy = _ins({"doctype": "EORL Tool Policy", "policy_name": f"{label} Policy", **flags,
			"allowed_semantic_tools": [{"tool_name": t} for t in tools]})
		agent = _ins({"doctype": "EORL Agent Template", "template_name": label, "organizational_role": label,
			"model_profile": profile.name, "tool_policy": policy.name})
		slots.append({"slot_id": key, "agent_template": agent.name})
	spec = _ins({"doctype": "EORL Architecture", "architecture_name": "Specialist Handoff",
		"coordination_mode": "specialist_handoff", "actor_slots": slots})

	policy = _ins({"doctype": "EORL Tool Policy", "policy_name": "General Purchasing Policy", "may_submit_documents": 1,
		"may_approve": 1, "may_message_agents": 1, "allowed_semantic_tools": [{"tool_name": t} for t in BROAD_TOOLS]})
	agent = _ins({"doctype": "EORL Agent Template", "template_name": "General Purchasing Agent",
		"organizational_role": "General Purchasing Agent", "model_profile": profile.name, "tool_policy": policy.name})
	broad = _ins({"doctype": "EORL Architecture", "architecture_name": "Broad Autonomy",
		"coordination_mode": "broad_autonomy", "actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": agent.name}]})

	shift = _ins({"doctype": "EORL Regime Shift", "shift_name": "Demand Surge at Episode 4", "trigger_episode": 4,
		"shift_type": "abrupt", "hidden_from_agents": 1, "parameter_delta_json": frappe.as_json({"qty_multiplier": 1.8})})

	exp = _ins({"doctype": "EORL Experiment", "experiment_name": "Specialist vs Broad Autonomy",
		"research_question": "Does broader autonomy change routine coherence and variety under a demand shock?",
		"architecture_a": spec.name, "architecture_b": broad.name, "regime_shift": shift.name,
		"episode_count": 6, "repetitions_per_cell": 5, "seed_strategy": "paired", "base_seed": 100})

	plan = _ins({"doctype": "EORL Analysis Plan", "plan_name": "Run-level actor continuity",
		"outcome_metric": "actor_continuity", "analysis_unit": "run", "permutation_iterations": 2000,
		"research_question": "Is actor continuity different between the two architectures?"})
	frappe.db.commit()
	print("config", spec.name, broad.name, shift.name, exp.name, plan.name)


def seed_pilot():
	exp = "Specialist vs Broad Autonomy"
	res = experiments_api.launch_pilot(exp)
	runs = res["runs"]
	frappe.db.commit()
	by = {}
	for r in runs:
		by.setdefault(r["architecture"], []).append(r["run"])
	print("pilot", json.dumps(by))
	return by


def seed_analysis():
	by = {}
	for r in frappe.get_all("EORL Run", fields=["name", "architecture_snapshot_json"], order_by="creation asc"):
		arch = json.loads(r.architecture_snapshot_json or "{}").get("architecture_name")
		by.setdefault(arch, []).append(r.name)
	a, b = by["Specialist Handoff"][:5], by["Broad Autonomy"][:5]
	for r in a + b:
		metrics_api.compute_run_metrics(r)
	res = analysis_api.compare_groups("Run-level actor continuity", a, b)
	frappe.db.commit()
	print("analysis", json.dumps({k: res[k] for k in res if k != "results"}, default=str)[:600])
	for r in res["results"]:
		print(" ", {k: r.get(k) for k in ("test", "p_value", "statistic")})


def seed_long_and_branch():
	long_run = run_architecture("Specialist Handoff", seed=7, episode_count=30)
	frappe.db.commit()
	print("long", long_run["run"], long_run["event_count"])
	src = frappe.get_all("EORL Run", filters={"name": ["!=", long_run["run"]]}, order_by="creation asc", limit=1, pluck="name")[0]
	br = runs_api.branch_run(src, 2, additional_episode_count=2, architecture_name="Broad Autonomy")
	frappe.db.commit()
	print("branch", json.dumps(br, default=str)[:400])


def seed_users():
	reviewer = os.environ["REVIEWER_USER"]
	if not frappe.db.exists("User", reviewer):
		frappe.get_doc({"doctype": "User", "email": reviewer, "first_name": "Reviewer", "send_welcome_email": 0,
			"user_type": "System User", "roles": [{"role": "EORL Viewer"}]}).insert(ignore_permissions=True)
	from frappe.utils.password import update_password
	update_password(reviewer, os.environ["REVIEWER_PASSWORD"])
	update_password("Administrator", os.environ["ADMIN_PASSWORD"])
	frappe.db.commit()
	u = frappe.get_doc("User", reviewer)
	print("reviewer roles", [r.role for r in u.roles], u.user_type, u.enabled)


def counts():
	for dt in ("EORL Run", "EORL Episode", "EORL Event", "EORL Metric", "EORL Analysis Result", "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry", "User"):
		print(dt, frappe.db.count(dt))
