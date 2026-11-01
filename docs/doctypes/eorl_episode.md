# EORL Episode

| Field | Type | Description |
|---|---|---|
| `run` (Run) | Link → `EORL Run` |  |
| `episode_number` (Episode Number) | Int |  |
| `phase` (Phase) | Select (warmup / stable / shock / recovery) |  |
| `status` (Status) | Select (pending / running / completed / failed) |  |
| `success` (Success) | Check |  |
| `utility` (Utility) | Float | Outcome utility v1: 0 if the episode did not complete, otherwise 1 minus the share of units rejected on inspection. |
| `failure_type` (Failure Type) | Data |  |
| `scenario_case_id` (Scenario Case ID) | Data |  |
| `environmental_state_hash` (Environmental State Hash) | Data |  |
| `ground_truth_json` (Ground Truth (JSON)) | Code |  |
| `started_at` (Started At) | Datetime |  |
| `ended_at` (Ended At) | Datetime |  |
| `cycle_steps` (Cycle Steps) | Int |  |
| `cycle_time_simulated` (Cycle Time (Simulated)) | Float |  |
| `cycle_time_wallclock` (Cycle Time (Wallclock, s)) | Float |  |
| `outcome_json` (Outcome (JSON)) | Code |  |
| `process_signature` (Process Signature) | Data |  |
