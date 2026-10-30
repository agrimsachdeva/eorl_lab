# EORL Tool Policy

| Field | Type | Description |
|---|---|---|
| `policy_name` (Policy Name) | Data |  |
| `allowed_semantic_tools` (Allowed Semantic Tools) | Table → `EORL Allowed Tool` |  |
| `has_execution_authority` (Execution Authority) | Check | May perform an authorized action. In practice this is redundant with a non-empty allowed_semantic_tools list; kept explicit for the formal model and so a policy can be defined with zero execution authority (observer-only) without clearing the tool list. |
| `has_decision_authority` (Decision Authority) | Check | May choose which course of action to take (e.g. which supplier) rather than following a prescribed script. Not yet enforced at runtime -- DeterministicProvider always exercises judgment -- but recorded so a future prescribed-process provider can check it. |
| `may_approve` (May Approve) | Check | This is the Approval Authority grant (V2 section 12 type 3). |
| `has_assignment_authority` (Assignment Authority) | Check | May allocate work to other actors. Ties into EORL Task Assignment; no policy in this system grants it yet since every architecture built so far has exactly one candidate per slot. |
| `allowed_read_scopes` (Allowed Read Scopes) | Small Text |  |
| `allowed_write_scopes` (Allowed Write Scopes) | Small Text |  |
| `allowed_docstatus_transitions` (Allowed Docstatus Transitions) | Small Text |  |
| `may_submit_documents` (May Submit Documents) | Check |  |
| `may_cancel_documents` (May Cancel Documents) | Check |  |
| `may_request_approval` (May Request Approval) | Check |  |
| `may_message_agents` (May Message Agents) | Check |  |
| `allowed_message_targets` (Allowed Message Targets) | Small Text |  |
| `max_tool_calls_per_step` (Max Tool Calls Per Step) | Int |  |
| `max_write_actions_per_episode` (Max Write Actions Per Episode) | Int |  |
| `escalation_policy` (Escalation Policy) | Small Text |  |
| `soft_rule_large_qty_threshold` (Large-Order Soft Threshold (Qty)) | Float | If set, a create_purchase_order call with qty above this value is still allowed, but logs a soft_rule_violation event (e.g. 'large purchases should have manager pre-approval'). Milestone scope: one concrete soft rule, not a general rule DSL. |
