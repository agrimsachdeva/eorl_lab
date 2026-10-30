# EORL Branch

| Field | Type | Description |
|---|---|---|
| `parent_run` (Parent Run) | Link → `EORL Run` |  |
| `source_episode` (Source Episode) | Int | The parent run's episode number this branch diverged from. Episodes 1..source_episode are shared, identical history (spec V2 section 17: 'History_A[1:t] == History_B[1:t]'). |
| `child_run` (Child Run) | Link → `EORL Run` |  |
| `intervention_description` (Intervention Description) | Small Text | What changed after the branch point (e.g. 'switched from specialist_handoff to broad_autonomy architecture'). |
| `created_at` (Created At) | Datetime |  |
