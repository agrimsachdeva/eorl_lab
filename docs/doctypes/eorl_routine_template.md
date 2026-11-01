# EORL Routine Template

| Field | Type | Description |
|---|---|---|
| `routine_name` (Routine Name) | Data |  |
| `version` (Version) | Data |  |
| `domain` (Domain) | Data |  |
| `description` (Description) | Small Text |  |
| `process_grammar` (Process Grammar) | Link → `EORL Process Grammar` |  |
| `required_tools` (Required Tools) | Small Text | Comma-separated semantic tool names the routine uses. |
| `default_roles` (Default Roles) | Small Text |  |
| `stage_sequence_json` (Stage Sequence) | Code | Ordered list of {role, slot, handoff_keys, tools, completes_on}. Specialist handoff runs one actor per entry in this order; broad autonomy runs one actor through all of them. |
| `scenario_generator` (Scenario Generator) | Data | Dotted path to generate_case(seed, episode, regime_shift, outcome_model). |
| `exogenous_state_function` (Exogenous State Function) | Data | Dotted path to exogenous_state(case, regime_shift). |
| `terminal_conditions` (Terminal Conditions) | Small Text | Comma-separated keys that must be present and truthy in the final routine state for an episode to count as complete. |
| `outcome_keys` (Outcome Keys) | Small Text | Comma-separated routine-state keys copied into each episode outcome. |
| `broad_slot` (Broad-Autonomy Slot) | Data |  |
| `broad_role` (Broad-Autonomy Role) | Data |  |
| `memory_domain` (Memory Domain) | Data |  |
| `default_metrics` (Default Metrics) | Small Text |  |
