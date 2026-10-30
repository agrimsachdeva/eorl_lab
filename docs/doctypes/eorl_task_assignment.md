# EORL Task Assignment

| Field | Type | Description |
|---|---|---|
| `run` (Run) | Link → `EORL Run` |  |
| `episode` (Episode) | Link → `EORL Episode` |  |
| `slot_id` (Slot ID) | Data |  |
| `assigned_to` (Assigned To) | Link → `EORL Agent Template` |  |
| `assignment_policy` (Assignment Policy) | Select (fixed / round_robin) |  |
| `candidate_count` (Candidate Count) | Int | Number of agents eligible for this slot. 1 for every architecture built so far (SOTA Milestone 1 does not yet support multi-candidate pools) -- recorded anyway so the assignment decision is a real, queryable record. |
| `rationale` (Rationale) | Small Text |  |
| `assigned_at` (Assigned At) | Datetime |  |
