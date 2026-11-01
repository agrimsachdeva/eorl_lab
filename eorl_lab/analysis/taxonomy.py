"""Action taxonomy and registered sequence views (submission-day plan
section 19).

The language-model pilot showed that optional read-only calls can move
sequence entropy on their own. Deleting those calls after the fact
would be a post hoc choice. Instead every tool carries a declared
category, and an Analysis Plan names the sequence view
(`sequence_scope`) its process measures use before any run is
launched. The same run then yields an all-action sequence and a
consequential-action sequence from one set of events, with no ad hoc
filtering.

Everything here is a plain mapping or a pure function, so it works on an
exported bundle outside Frappe like the rest of eorl_lab.analysis.
"""
from typing import Optional

TAXONOMY_VERSION = "v1"

# The seven categories named in the plan, plus `control` for the no-op
# finish_turn tool. `handoff` has no tool: orchestrator-enforced handoffs
# are agent_message_sent events, not tool results, so they never appear
# in a tool-result sequence.
CATEGORIES = ("sense", "communicate", "decide", "execute", "verify", "approve", "handoff", "control")

TOOL_CATEGORY = {
	# procure-to-pay
	"get_supplier_options": "sense",
	"get_purchase_order": "sense",
	"get_receipt_status": "sense",
	"create_purchase_order": "decide",  # carries the sourcing decision (which supplier)
	"submit_purchase_order": "approve",
	"create_purchase_receipt": "execute",
	"submit_purchase_receipt": "execute",
	"inspect_received_goods": "verify",
	"escalate_quality_exception": "execute",
	"create_purchase_invoice": "execute",
	"submit_purchase_invoice": "execute",
	"create_payment_entry": "execute",
	"submit_payment_entry": "execute",
	# order-to-cash (second routine)
	"get_customer_order": "sense",
	"get_sales_order": "sense",
	"get_delivery_status": "sense",
	"create_sales_order": "decide",
	"submit_sales_order": "approve",
	"create_delivery_note": "execute",
	"submit_delivery_note": "execute",
	"create_sales_invoice": "execute",
	"submit_sales_invoice": "execute",
	"create_customer_payment": "execute",
	"submit_customer_payment": "execute",
	# organization
	"message_agent": "communicate",
	"finish_turn": "control",
}

# The ERP object each tool reads or writes (an attribute for attribute-
# level path coherence).
TOOL_OBJECT_TYPE = {
	"get_supplier_options": "supplier",
	"get_purchase_order": "purchase_order",
	"create_purchase_order": "purchase_order",
	"submit_purchase_order": "purchase_order",
	"get_receipt_status": "purchase_receipt",
	"create_purchase_receipt": "purchase_receipt",
	"submit_purchase_receipt": "purchase_receipt",
	"inspect_received_goods": "purchase_receipt",
	"escalate_quality_exception": "quality_exception",
	"create_purchase_invoice": "purchase_invoice",
	"submit_purchase_invoice": "purchase_invoice",
	"create_payment_entry": "payment_entry",
	"submit_payment_entry": "payment_entry",
	"get_customer_order": "customer",
	"get_sales_order": "sales_order",
	"create_sales_order": "sales_order",
	"submit_sales_order": "sales_order",
	"get_delivery_status": "delivery_note",
	"create_delivery_note": "delivery_note",
	"submit_delivery_note": "delivery_note",
	"create_sales_invoice": "sales_invoice",
	"submit_sales_invoice": "sales_invoice",
	"create_customer_payment": "payment_entry",
	"submit_customer_payment": "payment_entry",
	"message_agent": "message",
	"finish_turn": "none",
}

# The organizational decision domain a tool belongs to.
TOOL_DECISION_DOMAIN = {
	"get_supplier_options": "sourcing",
	"create_purchase_order": "sourcing",
	"get_purchase_order": "approval",
	"submit_purchase_order": "approval",
	"create_purchase_receipt": "receiving",
	"submit_purchase_receipt": "receiving",
	"inspect_received_goods": "quality",
	"escalate_quality_exception": "quality",
	"get_receipt_status": "payables",
	"create_purchase_invoice": "payables",
	"submit_purchase_invoice": "payables",
	"create_payment_entry": "payables",
	"submit_payment_entry": "payables",
	"get_customer_order": "sales",
	"create_sales_order": "sales",
	"get_sales_order": "sales",
	"submit_sales_order": "sales",
	"create_delivery_note": "fulfillment",
	"submit_delivery_note": "fulfillment",
	"get_delivery_status": "billing",
	"create_sales_invoice": "billing",
	"submit_sales_invoice": "billing",
	"create_customer_payment": "collection",
	"submit_customer_payment": "collection",
	"message_agent": "communication",
	"finish_turn": "control",
}

# Registered sequence views. `all_actions` is the original Milestone 7
# definition (every tool result, including finish_turn) and stays the
# default so existing results keep their meaning.
SEQUENCE_SCOPES = ("all_actions", "consequential_actions", "write_actions", "actor_function_actions")

_NON_CONSEQUENTIAL = {"sense", "control"}
_WRITE_CATEGORIES = {"decide", "execute", "approve"}

# Tools whose arguments carry the substantive decision. In the
# consequential view their token is annotated with that choice, so two
# episodes that order from different suppliers follow different paths.
# The all_actions view is never annotated, which keeps it identical to
# the Milestone 7 definition.
DECISION_ATTRIBUTE_BY_TOOL = {
	"create_purchase_order": "supplier",
	"create_sales_order": "customer",
}


def category_for(tool_name: Optional[str]) -> str:
	return TOOL_CATEGORY.get(tool_name or "", "execute")


def in_scope(tool_name: Optional[str], scope: str) -> bool:
	if scope not in SEQUENCE_SCOPES:
		raise ValueError(f"Unknown sequence_scope {scope!r}; registered scopes are {SEQUENCE_SCOPES}")
	category = category_for(tool_name)
	if scope == "all_actions":
		return True
	if scope in ("consequential_actions", "actor_function_actions"):
		return category not in _NON_CONSEQUENTIAL
	if scope == "write_actions":
		return category in _WRITE_CATEGORIES
	return True


def scope_metric_name(metric_name: str, scope: Optional[str]) -> str:
	"""Persisted name of a scoped metric. The default scope keeps the
	bare name so every result computed before scopes existed still
	resolves."""
	if not scope or scope == "all_actions":
		return metric_name
	return f"{metric_name}@{scope}"
