# EORL Event

| Field | Type | Description |
|---|---|---|
| `run` (Run) | Link → `EORL Run` |  |
| `episode` (Episode) | Link → `EORL Episode` |  |
| `sequence_no` (Sequence No) | Int |  |
| `event_type` (Event Type) | Select (run_initialized / run_branched / run_marked_ablation / episode_initialized / environment_observed / agent_context_built / memory_query / memory_retrieval / agent_message_sent / agent_message_received / model_request / model_response / decision_parsed / tool_requested / tool_authorized / tool_denied / tool_result / soft_rule_violation / task_assigned / erp_state_before / erp_mutation / erp_state_after / memory_write / episode_outcome / metric_computed / error / run_completed) |  |
| `wallclock_timestamp` (Wallclock Timestamp) | Datetime |  |
| `simulated_timestamp` (Simulated Timestamp) | Data |  |
| `success` (Success) | Check |  |
| `actor_slot` (Actor Slot) | Data |  |
| `actor_instance_id` (Actor Instance ID) | Data |  |
| `trace_id` (Trace ID) | Data |  |
| `span_id` (Span ID) | Data |  |
| `parent_span_id` (Parent Span ID) | Data |  |
| `correlation_id` (Correlation ID) | Data |  |
| `target_type` (Target Type) | Data |  |
| `target_id` (Target ID) | Data |  |
| `payload_json` (Payload (JSON)) | Code |  |
| `payload_hash` (Payload Hash) | Data |  |
