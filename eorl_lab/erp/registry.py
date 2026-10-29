from eorl_lab.erp import buying

# Milestone 2 registers only the two tools the vertical slice needs. Later
# milestones extend this registry (section 10's full read/write/communication
# tool list) without changing how the orchestrator or authority firewall
# look tools up.
TOOL_REGISTRY = {
	"get_supplier_options": buying.get_supplier_options,
	"create_purchase_order": buying.create_purchase_order,
}


def get_tool(tool_name: str):
	if tool_name not in TOOL_REGISTRY:
		raise KeyError(f"Unknown or unregistered semantic tool: {tool_name}")
	return TOOL_REGISTRY[tool_name]
