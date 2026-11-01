# EORL Metric

| Field | Type | Description |
|---|---|---|
| `run` (Run) | Link → `EORL Run` |  |
| `episode` (Episode) | Link → `EORL Episode` | Blank for run-level metrics (e.g. sequence entropy across all episodes). |
| `phase` (Phase) | Select ( / warmup / stable / shock / recovery) | Blank unless the metric is itself phase-scoped (e.g. post-shock error rate). |
| `metric_name` (Metric Name) | Data |  |
| `metric_value` (Metric Value) | Float |  |
| `value_undefined` (Value Undefined) | Check | Set when the metric has no defined value for this run (Frappe stores an empty number as 0, so metric_value is then 0 and meaningless). |
| `metric_version` (Metric Version) | Data | Versions the computation, not just the DocType, per spec section 17.3's explicit instruction to version e.g. the viable-path criterion. |
| `computed_at` (Computed At) | Datetime |  |
| `metric_json` (Metric Detail (JSON)) | Code | Structured detail that doesn't fit a single float (e.g. a directly-follows graph, a communication network, or the viable-path set itself). |
