from eorl_lab.erp import buying, stock
from eorl_lab.organization import communication, control

# Milestone 3 extended the registry to cover the full procure-to-pay
# chain. SOTA Milestone 1 adds the ground-truth-driven inspection/
# exception tools (V2 section 15) and the first agent-chosen
# communication tool (V2 section 9) -- message_agent, checked against a
# real EORL Communication Policy graph, used alongside (not instead of)
# the orchestrator-enforced structural handoffs (eorl_lab.runtime
# .orchestrator._handoff) that still drive the normal specialist/handoff
# stage sequence.
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
	"inspect_received_goods": stock.inspect_received_goods,
	"escalate_quality_exception": stock.escalate_quality_exception,
	"message_agent": communication.message_agent,
	# SOTA Milestone 3: a real model provider needs an explicit tool to
	# signal "my turn is done" (see eorl_lab.organization.control.finish_turn).
	"finish_turn": control.finish_turn,
}


def get_tool(tool_name: str):
	if tool_name not in TOOL_REGISTRY:
		raise KeyError(f"Unknown or unregistered semantic tool: {tool_name}")
	return TOOL_REGISTRY[tool_name]
