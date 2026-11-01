"""Routine templates (submission-day plan section 2.1).

A routine template tells the orchestrator everything that is specific
to one organizational routine: which roles act in which order, what
each hands to the next, which tools belong to each stage, how a case is
generated, and what has to be true at the end for an episode to count
as complete. The orchestrator itself names no routine.

The two definitions below are the built-in defaults. `EORL Routine
Template` documents are seeded from them (seed_routine_templates) and
can be edited or added to; resolve_routine() prefers a document when an
architecture names one and falls back to Procure-to-Pay otherwise, which
is what every architecture built before routine templates implicitly
used.
"""
import copy
import json

import frappe

DEFAULT_ROUTINE = "Procure-to-Pay"

BUILTIN_ROUTINES = {
	"Procure-to-Pay": {
		"description": "Purchase requisition through supplier payment: order, approve, receive and inspect, invoice, pay.",
		"domain": "procurement",
		"version": "1",
		"scenario_generator": "eorl_lab.scenarios.procurement.generate_case",
		"exogenous_state_function": "eorl_lab.scenarios.procurement.exogenous_state",
		"memory_domain": "procurement",
		"broad_slot": "general_purchasing_agent",
		"broad_role": "General Purchasing Agent",
		"terminal_conditions": ["purchase_order", "purchase_receipt_submitted", "payment_entry_submitted"],
		"outcome_keys": ["purchase_order", "purchase_receipt", "purchase_invoice", "payment_entry", "quality_passed"],
		"default_metrics": ["modal_path_share", "sequence_entropy", "actor_continuity", "path_coherence_v1"],
		"stages": [
			{"role": "Purchasing Agent", "slot": "purchasing_agent", "handoff_keys": [],
				"tools": ["get_supplier_options", "create_purchase_order"], "completes_on": "purchase_order"},
			{"role": "Purchasing Manager Agent", "slot": "purchasing_manager_agent", "handoff_keys": ["purchase_order"],
				"tools": ["get_purchase_order", "submit_purchase_order"], "completes_on": "purchase_order_submitted"},
			{"role": "Warehouse Agent", "slot": "warehouse_agent", "handoff_keys": ["purchase_order"],
				"tools": ["get_purchase_order", "create_purchase_receipt", "inspect_received_goods",
					"escalate_quality_exception", "message_agent", "submit_purchase_receipt"],
				"completes_on": "purchase_receipt_submitted"},
			{"role": "Accounts Payable Agent", "slot": "accounts_payable_agent", "handoff_keys": ["purchase_receipt"],
				"tools": ["get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice",
					"create_payment_entry", "submit_payment_entry"],
				"completes_on": "payment_entry_submitted"},
		],
	},
	"Order-to-Cash": {
		"description": "Customer order through cash collection: take and confirm the order, deliver, invoice, collect.",
		"domain": "sales",
		"version": "1",
		"scenario_generator": "eorl_lab.scenarios.order_to_cash.generate_case",
		"exogenous_state_function": "eorl_lab.scenarios.order_to_cash.exogenous_state",
		"memory_domain": "sales",
		"broad_slot": "general_order_agent",
		"broad_role": "General Order Agent",
		"terminal_conditions": ["sales_order_submitted", "delivery_note_submitted", "customer_payment_submitted"],
		"outcome_keys": ["sales_order", "delivery_note", "sales_invoice", "customer_payment"],
		"default_metrics": ["modal_path_share", "sequence_entropy", "actor_continuity", "path_coherence_v1"],
		"stages": [
			{"role": "Sales Agent", "slot": "sales_agent", "handoff_keys": [],
				"tools": ["get_customer_order", "create_sales_order", "submit_sales_order"], "completes_on": "sales_order_submitted"},
			{"role": "Fulfillment Agent", "slot": "fulfillment_agent", "handoff_keys": ["sales_order"],
				"tools": ["get_sales_order", "create_delivery_note", "submit_delivery_note"], "completes_on": "delivery_note_submitted"},
			{"role": "Billing Agent", "slot": "billing_agent", "handoff_keys": ["delivery_note"],
				"tools": ["get_delivery_status", "create_sales_invoice", "submit_sales_invoice",
					"create_customer_payment", "submit_customer_payment"],
				"completes_on": "customer_payment_submitted"},
		],
	},
}

# Process grammars seeded alongside the templates: one stage per process
# stage in eorl_lab.analysis.paths.PROCESS_STAGE_BY_TOOL.
BUILTIN_GRAMMARS = {
	"Procure-to-Pay Grammar": ["SUPPLIER_SEARCH", "PURCHASE_ORDER", "APPROVAL", "RECEIPT", "EXCEPTION", "INVOICE", "PAYMENT"],
	"Order-to-Cash Grammar": ["ORDER_INTAKE", "SALES_ORDER", "ORDER_APPROVAL", "FULFILLMENT", "BILLING", "COLLECTION"],
}
GRAMMAR_FOR_ROUTINE = {"Procure-to-Pay": "Procure-to-Pay Grammar", "Order-to-Cash": "Order-to-Cash Grammar"}


def resolve_routine(name=None) -> dict:
	"""The routine definition as a plain dict, with `name` set."""
	name = name or DEFAULT_ROUTINE
	if frappe.db.exists("EORL Routine Template", name):
		doc = frappe.get_doc("EORL Routine Template", name)
		definition = doc.to_definition()
	elif name in BUILTIN_ROUTINES:
		definition = copy.deepcopy(BUILTIN_ROUTINES[name])
	else:
		frappe.throw(f"Unknown routine template: {name!r}")
	definition["name"] = name
	return definition


def required_tools(definition: dict) -> list:
	tools = []
	for stage in definition["stages"]:
		for tool in stage["tools"]:
			if tool not in tools:
				tools.append(tool)
	return tools


def seed_routine_templates():
	"""Idempotent: inserts the built-in grammars and templates that are
	missing and leaves existing documents alone."""
	from eorl_lab.analysis.paths import PROCESS_STAGE_BY_TOOL

	for grammar_name, stages in BUILTIN_GRAMMARS.items():
		if not frappe.db.exists("EORL Process Grammar", grammar_name):
			transitions, previous = [], None
			for code in stages:
				tools = [t for t, stage in PROCESS_STAGE_BY_TOOL.items() if stage == code]
				transitions.append({"from_stage": previous, "to_stage": code, "transition_type": "mandatory", "tool_names": ", ".join(tools)})
				previous = code
			frappe.get_doc({
				"doctype": "EORL Process Grammar", "grammar_name": grammar_name,
				"description": f"Stages of the built-in {grammar_name.replace(' Grammar', '')} routine.",
				"stages": [{"stage_id": code, "label": code.replace("_", " ").title(), "is_terminal": 1 if i == len(stages) - 1 else 0}
					for i, code in enumerate(stages)],
				"transitions": transitions,
			}).insert(ignore_permissions=True)

	for name, definition in BUILTIN_ROUTINES.items():
		if frappe.db.exists("EORL Routine Template", name):
			continue
		frappe.get_doc({
			"doctype": "EORL Routine Template",
			"routine_name": name,
			"description": definition["description"],
			"domain": definition["domain"],
			"version": definition["version"],
			"process_grammar": GRAMMAR_FOR_ROUTINE[name],
			"scenario_generator": definition["scenario_generator"],
			"exogenous_state_function": definition["exogenous_state_function"],
			"memory_domain": definition["memory_domain"],
			"broad_slot": definition["broad_slot"],
			"broad_role": definition["broad_role"],
			"required_tools": ", ".join(required_tools(definition)),
			"terminal_conditions": ", ".join(definition["terminal_conditions"]),
			"outcome_keys": ", ".join(definition["outcome_keys"]),
			"default_roles": ", ".join(s["role"] for s in definition["stages"]),
			"default_metrics": ", ".join(definition["default_metrics"]),
			"stage_sequence_json": json.dumps(definition["stages"], indent=1),
		}).insert(ignore_permissions=True)
