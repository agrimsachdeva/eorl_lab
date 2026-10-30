# EORL Architecture Actor Slot

*Child table.*

| Field | Type | Description |
|---|---|---|
| `slot_id` (Slot ID) | Data | Stable key the orchestrator's coordination_mode handler looks up, e.g. 'purchasing_agent' or 'general_purchasing_agent'. |
| `agent_template` (Agent Template) | Link → `EORL Agent Template` |  |
| `count` (Count) | Int |  |
