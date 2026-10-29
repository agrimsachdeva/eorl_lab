from eorl_lab.erp import buying

# Milestone 3 extends the registry to cover the full procure-to-pay chain
# (spec section 10): sensing + consequential actions for PO approval,
# receipt, invoice, and payment. Communication tools (message_agent,
# request_approval, escalate_exception) remain structural/orchestrated for
# the specialist/handoff architecture in this milestone -- see
# eorl_lab.runtime.orchestrator._handoff -- rather than agent-chosen tool
# calls; that becomes relevant once a broader-autonomy architecture is
# introduced (spec section 2.3 Architecture B, a later milestone).
TOOL_REGISTRY = {
	"get_supplier_options": buying.get_supplier_options,
	"get_purchase_order": buying.get_purchase_order,
	"get_receipt_status": buying.get_receipt_status,
	"create_purchase_order": buying.create_purchase_order,
	"submit_purchase_order": buying.submit_purchase_order,
	"create_purchase_receipt": buying.create_purchase_receipt,
	"submit_purchase_receipt": buying.submit_purchase_receipt,
	"create_purchase_invoice": buying.create_purchase_invoice,
	"submit_purchase_invoice": buying.submit_purchase_invoice,
	"create_payment_entry": buying.create_payment_entry,
	"submit_payment_entry": buying.submit_payment_entry,
}


def get_tool(tool_name: str):
	if tool_name not in TOOL_REGISTRY:
		raise KeyError(f"Unknown or unregistered semantic tool: {tool_name}")
	return TOOL_REGISTRY[tool_name]
