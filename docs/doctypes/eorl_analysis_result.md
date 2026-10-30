# EORL Analysis Result

| Field | Type | Description |
|---|---|---|
| `analysis_plan` (Analysis Plan) | Link → `EORL Analysis Plan` |  |
| `experiment` (Experiment) | Link → `EORL Experiment` |  |
| `test_family` (Test Family) | Data | Which test actually produced THIS result row (e.g. 'welch_t', 'permutation', 'paired_t', 'paired_permutation') -- compare_groups always computes more than one test family per call and writes one EORL Analysis Result per family, so nothing is silently chosen for the researcher (V2 section 44.4). |
| `run_ids_group_a` (Run IDs (Group A)) | Small Text | Comma-separated EORL Run names. |
| `run_ids_group_b` (Run IDs (Group B)) | Small Text |  |
| `n_independent_runs_a` (N Independent Runs (A)) | Int |  |
| `n_independent_runs_b` (N Independent Runs (B)) | Int |  |
| `n_episodes_a` (N Episodes (A)) | Int | Shown alongside N Independent Runs so the two are never confused (V2 section 44.2) -- never the sample size the test itself used. |
| `n_episodes_b` (N Episodes (B)) | Int |  |
| `paired` (Paired Comparison) | Check | True if this result came from a paired/matched test (counterfactual branch pairs, V2 section 44.3), false for an ordinary independent-groups test. |
| `metric_definition_version` (Metric Definition Version) | Data | The EORL Metric.metric_version actually used for every run's outcome value. |
| `code_commit` (Code Commit) | Data |  |
| `stats_package_version` (Statistics Package Version) | Data | e.g. 'scipy 1.15.3' -- which library and version actually computed this result. |
| `mean_a` (Mean (A)) | Float |  |
| `mean_b` (Mean (B)) | Float |  |
| `raw_effect` (Raw Effect (Mean Difference)) | Float |  |
| `standardized_effect` (Standardized Effect (Hedges' g)) | Float |  |
| `ci_95_lower` (95% CI Lower) | Float |  |
| `ci_95_upper` (95% CI Upper) | Float |  |
| `p_value` (p-value) | Float |  |
| `adjusted_p_value` (Adjusted p-value) | Float | Reserved (V2 section 46, multiple-testing correction) -- left blank; not implemented yet. |
| `diagnostics_json` (Diagnostics (JSON)) | Code | The complete raw dict returned by eorl_lab.analysis.stats (t-statistic/df for t-tests, n_iterations for permutation tests, etc.) -- the fields above are the commonly-reported subset, this is the full record. |
