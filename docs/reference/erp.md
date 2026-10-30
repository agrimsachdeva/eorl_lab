# ERP Tools

The semantic ERP adapter: the actual tool functions an agent can call,
each a real ERPNext document operation, each registered in
`eorl_lab.erp.registry.TOOL_REGISTRY`. The orchestrator's
`_call_tool_with_context` injects `_case` / `_sender_slot` /
`_communication_policy` only into tools that declare those exact
parameter names — an agent can never supply them itself.

::: eorl_lab.erp.registry

::: eorl_lab.erp.buying

::: eorl_lab.erp.stock
