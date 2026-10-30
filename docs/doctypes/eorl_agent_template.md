# EORL Agent Template

| Field | Type | Description |
|---|---|---|
| `template_name` (Template Name) | Data |  |
| `organizational_role` (Organizational Role) | Data |  |
| `enabled` (Enabled) | Check |  |
| `role_description` (Role Description) | Text |  |
| `responsibilities` (Responsibilities) | Text |  |
| `local_goal` (Local Goal) | Text |  |
| `global_goal_context` (Global Goal Context) | Text |  |
| `information_scope` (Information Scope) | Text |  |
| `authority_description` (Authority Description) | Text | Descriptive only. Actual authority is enforced by the EORL Tool Policy / authority firewall, not by this text. |
| `model_profile` (Model Profile) | Link → `EORL Model Profile` |  |
| `memory_profile` (Memory Profile) | Link → `EORL Memory Profile` |  |
| `tool_policy` (Tool Policy) | Link → `EORL Tool Policy` |  |
| `initial_system_instructions` (Initial System Instructions) | Code |  |
| `decision_schema_version` (Decision Schema Version) | Data |  |
| `communication_enabled` (Communication Enabled) | Check |  |
| `max_messages_per_episode` (Max Messages Per Episode) | Int |  |
| `max_decisions_per_episode` (Max Decisions Per Episode) | Int |  |
| `local_goal_weight` (Local Goal Weight) | Float |  |
| `global_goal_weight` (Global Goal Weight) | Float |  |
| `compliance_weight` (Compliance Weight) | Float |  |
| `search_budget` (Search Budget) | Int |  |
| `communication_budget` (Communication Budget) | Int |  |
