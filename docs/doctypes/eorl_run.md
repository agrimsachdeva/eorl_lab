# EORL Run

| Field | Type | Description |
|---|---|---|
| `status` (Status) | Select (queued / initializing / running / completed / failed / aborted / cancelled) |  |
| `run_seed` (Run Seed) | Int |  |
| `current_episode` (Current Episode) | Int |  |
| `experiment` (Experiment) | Link → `EORL Experiment` |  |
| `cell_id` (Cell) | Data |  |
| `routine_template` (Routine Template) | Data |  |
| `actor_engine` (Actor Engine) | Data |  |
| `parent_run` (Parent Run) | Link → `EORL Run` |  |
| `branch_point_episode` (Branch Point Episode) | Int | The parent run's episode number this run diverged from. Episodes 1..branch_point_episode are owned by the parent, never duplicated -- see eorl_lab.runtime.orchestrator.get_full_branch_history. |
| `is_ablation_of` (Is Ablation Of) | Link → `EORL Run` |  |
| `ablation_mechanism` (Ablation Mechanism) | Small Text | What was toggled relative to is_ablation_of, e.g. 'memory_disabled', 'tool_breadth_reduced', 'communication_removed' (V2 section 19's example mechanisms). |
| `started_at` (Started At) | Datetime |  |
| `ended_at` (Ended At) | Datetime |  |
| `architecture_snapshot_json` (Architecture Snapshot (JSON)) | Code |  |
| `agent_snapshots_json` (Agent Snapshots (JSON)) | Code |  |
| `scenario_snapshot_json` (Scenario Snapshot (JSON)) | Code |  |
| `regime_shift_snapshot_json` (Regime Shift Snapshot (JSON)) | Code |  |
| `provider_snapshots_json` (Provider Snapshots (JSON)) | Code |  |
| `code_commit` (Code Commit) | Data |  |
| `app_version` (App Version) | Data |  |
| `erpnext_version` (ERPNext Version) | Data |  |
| `frappe_version` (Frappe Version) | Data |  |
| `site_fingerprint` (Site Fingerprint) | Data |  |
| `run_manifest_hash` (Run Manifest Hash) | Data |  |
| `failure_reason` (Failure Reason) | Small Text |  |
| `failure_type` (Failure Type) | Select ( / model_timeout / model_parse_error / tool_error / erp_validation_error / authority_denial_expected / authority_denial_unexpected / infrastructure_error / terminal_condition_not_met / max_turns_exceeded) |  |
| `retryable` (Retryable) | Check |  |
| `retry_count` (Provider Retries) | Int |  |
| `event_count` (Event Count) | Int |  |
| `total_tokens` (Total Tokens) | Int |  |
| `input_tokens` (Input Tokens) | Int |  |
| `output_tokens` (Output Tokens) | Int |  |
| `model_calls` (Model Calls) | Int |  |
| `wallclock_seconds` (Wallclock Seconds) | Float |  |
| `total_cost` (Total Cost) | Float |  |
