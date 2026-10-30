# EORL Settings

| Field | Type | Description |
|---|---|---|
| `enabled` (Enabled) | Check |  |
| `default_lab_company` (Default Lab Company) | Link → `Company` |  |
| `default_timezone` (Default Timezone) | Data |  |
| `default_provider_profile` (Default Provider Profile) | Link → `EORL Model Profile` |  |
| `default_max_episode_steps` (Default Max Episode Steps) | Int |  |
| `default_wallclock_timeout_seconds` (Default Wallclock Timeout (s)) | Int |  |
| `local_run_worker_queue` (Local Run Worker Queue) | Data |  |
| `max_parallel_local_runs` (Max Parallel Local Runs) | Int |  |
| `default_event_storage_mode` (Default Event Storage Mode) | Select (Frappe DB / JSONL / Both) |  |
| `artifact_export_root` (Artifact Export Root) | Data |  |
| `enable_cost_tracking` (Enable Cost Tracking) | Check |  |
| `enable_prompt_snapshotting` (Enable Prompt Snapshotting) | Check |  |
| `enable_erp_diff_capture` (Enable ERP Diff Capture) | Check |  |
| `enable_memory_snapshotting` (Enable Memory Snapshotting) | Check |  |
| `allow_proprietary_models` (Allow Proprietary Models) | Check |  |
| `canonical_seed` (Canonical Seed) | Int |  |
| `external_worker_callback_secret_reference` (External Worker Callback Secret Reference) | Data | Key/reference only. Do not store the secret value itself here; resolve from site config or environment. |
