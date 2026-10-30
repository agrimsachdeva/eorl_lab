# EORL Architecture

| Field | Type | Description |
|---|---|---|
| `architecture_name` (Architecture Name) | Data |  |
| `description` (Description) | Small Text |  |
| `coordination_mode` (Coordination Mode) | Select (specialist_handoff / broad_autonomy) |  |
| `central_coordinator_slot` (Central Coordinator Slot) | Data |  |
| `actor_slots` (Actor Slots) | Table → `EORL Architecture Actor Slot` |  |
| `communication_policy` (Communication Policy) | Link → `EORL Communication Policy` | SOTA Milestone 1: the actually-enforced communication graph for agent-chosen messaging (eorl_lab.organization.communication.message_agent). Supersedes communication_edges_json below, which stays inert JSON. |
| `process_grammar` (Process Grammar) | Link → `EORL Process Grammar` | SOTA Milestone 1: optional override of the default tool->stage mapping used when extracting this architecture's runs' process paths. Leave blank to use eorl_lab.analysis.paths.PROCESS_STAGE_BY_TOOL. |
| `supervision_edges_json` (Supervision Edges (JSON)) | Code |  |
| `communication_edges_json` (Communication Edges (JSON, unused -- see communication_policy)) | Code |  |
| `workflow_handoff_rules_json` (Workflow Handoff Rules (JSON)) | Code |  |
| `decision_right_assignments_json` (Decision-Right Assignments (JSON)) | Code |  |
| `shared_memory_assignment_json` (Shared-Memory Assignment (JSON)) | Code |  |
| `allowed_cross_stage_actions_json` (Allowed Cross-Stage Actions (JSON)) | Code |  |
| `escalation_graph_json` (Escalation Graph (JSON)) | Code |  |
| `approval_graph_json` (Approval Graph (JSON)) | Code |  |
