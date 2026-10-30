# EORL Memory Profile

| Field | Type | Description |
|---|---|---|
| `profile_name` (Profile Name) | Data |  |
| `local_memory_enabled` (Local Memory Enabled) | Check |  |
| `local_backend` (Local Backend) | Select (recent / episodic / semantic / procedural / vector / none) |  |
| `local_retention_episodes` (Local Retention Episodes) | Int |  |
| `local_top_k` (Local Top K) | Int |  |
| `recency_weight` (Recency Weight) | Float |  |
| `similarity_weight` (Similarity Weight) | Float |  |
| `outcome_weight` (Outcome Weight) | Float |  |
| `summarization_enabled` (Summarization Enabled) | Check |  |
| `summary_interval` (Summary Interval) | Int |  |
| `forgetting_enabled` (Forgetting Enabled) | Check |  |
| `forgetting_half_life` (Forgetting Half-Life) | Float |  |
| `shared_memory_enabled` (Shared Memory Enabled) | Check |  |
| `shared_backend` (Shared Backend) | Data |  |
| `shared_visibility_scope` (Shared Visibility Scope) | Data |  |
| `shared_write_policy` (Shared Write Policy) | Select (all / successes_only / curated / none) |  |
| `shared_top_k` (Shared Top K) | Int |  |
| `embedding_model_profile` (Embedding Model Profile) | Link → `EORL Model Profile` |  |
