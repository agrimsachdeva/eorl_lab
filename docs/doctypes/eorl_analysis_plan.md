# EORL Analysis Plan

| Field | Type | Description |
|---|---|---|
| `plan_name` (Plan Name) | Data |  |
| `version` (Version) | Data |  |
| `experiment` (Experiment) | Link → `EORL Experiment` | V2 section 44.1: 'The plan should be saved before inferential results are generated.' |
| `research_question` (Research Question) | Small Text |  |
| `estimand` (Estimand) | Small Text | What quantity this plan actually estimates (e.g. 'mean difference in sequence entropy between broad_autonomy and specialist_handoff'). |
| `outcome_metric` (Outcome Metric) | Data | An EORL Metric.metric_name this plan compares (e.g. 'sequence_entropy', 'actor_continuity', 'success_rate') -- computed per RUN via eorl_lab.api.metrics.compute_run_metrics, never per episode for a between-condition comparison (see analysis_unit below). |
| `sequence_scope` (Sequence Scope) | Select (all_actions / consequential_actions / write_actions / actor_function_actions) | Registered sequence view for process measures (eorl_lab.analysis.taxonomy). Must be set before launch. Ignored for metrics that do not depend on the sequence. |
| `factors` (Factor(s)) | Small Text | Free-text description of which factor(s) define the groups being compared (e.g. 'coordination_structure'). Group membership itself is supplied by the caller of eorl_lab.api.analysis.compare_groups as two lists of run names, not derived automatically from this field. |
| `contrast` (Contrast) | Data | e.g. 'Broad Autonomy vs Specialist Handoff'. |
| `analysis_unit` (Analysis Unit) | Select (run / episode) | V2 section 44.2's independence guardrail: 'Episodes inside one run are NOT independent replications.' eorl_lab.api.analysis.compare_groups REFUSES to run a between-condition comparison when this is 'episode' -- there is no mixed-effects/GEE path built yet (P1), so there is no honest hierarchical alternative to fall back to; it blocks outright rather than silently treating episodes as independent. |
| `cluster_unit` (Cluster Unit) | Data | Descriptive only in this phase (e.g. 'run') -- displayed alongside N independent runs / N episodes per V2 section 44.2's UI requirement; not yet fed into a clustered/mixed-effects model. |
| `paired_by` (Paired By) | Data | Set to 'branch_point' to declare that the two compared groups are matched, equal-length, position-corresponding sibling counterfactual branches (V2 section 44.3) -- eorl_lab.api.analysis.compare_groups then VERIFIES every pair actually shares a common parent_run/branch_point_episode before running paired tests, and throws rather than silently falling back to an independent-groups test if that verification fails. Leave blank for an ordinary independent-groups comparison. |
| `time_window` (Time Window) | Small Text | Descriptive only in this phase -- e.g. 'episodes 1-10' or 'pre-shock only'. Not yet enforced by compare_groups; filter the run/episode sets passed in yourself. |
| `regime` (Regime) | Link → `EORL Regime Shift` |  |
| `model_family` (Model Family) | Select (welch_t / permutation / paired_t / paired_permutation / mixed_effects) | Which test family eorl_lab.api.analysis.compare_groups actually runs. V2 section 44.4: the system may RECOMMEND a test but must never silently select one -- compare_groups always computes and returns BOTH the parametric and permutation result for the chosen pairing mode (independent or paired), regardless of this field; this field only labels which one the researcher intends to report as primary. EXCEPTION: when analysis_unit='episode' (SOTA Milestone 6), this field is REQUIRED to be 'mixed_effects' -- that is the one case compare_groups actually reads and enforces this field, since it is the only hierarchical model honestly justifying episode-level analysis at all. |
| `formula` (Formula) | Small Text | Reserved for the model-based test families (linear model / GLM / mixed model) named in V2 section 44.4 -- not implemented yet (P1); this field is not read by compare_groups today. |
| `covariates` (Covariates) | Small Text | Reserved, same P1 scope as Formula above. |
| `multiple_testing_family` (Multiple Testing Family) | Data | Reserved (V2 section 46) -- no multiple-testing correction is applied yet; not implemented. |
| `adjustment_method` (Adjustment Method) | Select (none / holm / benjamini_hochberg / bonferroni) | Applied across every plan sharing the same multiple_testing_family, to each plan's primary test. |
| `alpha` (Alpha) | Float |  |
| `equivalence_bounds` (Equivalence Bounds) | Small Text | Reserved (V2 section 45.1, TOST equivalence testing) -- not implemented yet; not read by compare_groups. |
| `bootstrap_iterations` (Bootstrap Iterations) | Int | Reserved -- no bootstrap CI is implemented in this phase; the Welch CI uses the standard closed-form Welch-Satterthwaite interval instead. |
| `permutation_iterations` (Permutation Iterations) | Int |  |
| `random_seed` (Random Seed) | Int | Seed for the permutation test and the bootstrap interval on Hedges' g, so a stored result can be recomputed exactly. |
| `exclusion_rule` (Exclusion Rule) | Small Text | Descriptive only in this phase -- not enforced automatically; exclude runs from the lists you pass to compare_groups yourself. |
| `expected_direction` (Expected Direction) | Select (a_greater / b_greater / nonzero) |  |
| `rival_prediction` (Rival Prediction) | Small Text |  |
| `support_rule` (If significant in the predicted direction) | Select (consistent / inconsistent / inconclusive) |  |
| `contradiction_rule` (If significant in the opposite direction) | Select (consistent / inconsistent / inconclusive) |  |
| `equivalence_rule` (If not significant and equivalence established) | Select (consistent / inconsistent / inconclusive) |  |
| `inconclusive_rule` (If not significant and equivalence not established) | Select (consistent / inconsistent / inconclusive) |  |
| `trivial_effect_rule` (If significant but inside the equivalence bounds) | Select (consistent / inconsistent / inconclusive) |  |
| `interpretation_weight` (Weight (weighted combination only)) | Float |  |
