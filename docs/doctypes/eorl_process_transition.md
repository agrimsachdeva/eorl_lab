# EORL Process Transition

*Child table.*

| Field | Type | Description |
|---|---|---|
| `from_stage` (From Stage) | Data | Blank for an entry transition (the first stage of an episode). |
| `to_stage` (To Stage) | Data |  |
| `transition_type` (Transition Type) | Select (mandatory / optional / prohibited) |  |
| `tool_names` (Tool Names) | Small Text | Comma-separated semantic tool names that realize this transition (calling one of them moves the process to to_stage). |
