# EORL Experiment

| Field | Type | Description |
|---|---|---|
| `experiment_name` (Experiment Name) | Data |  |
| `status` (Status) | Select (draft / validated / pilot_launched / completed / failed) |  |
| `experiment_type` (Experiment Type) | Select (infrastructure_validation / theory_demonstration / empirical_study) | infrastructure_validation: checks that the instrument works (scripted actors). theory_demonstration: illustrates what a theory looks like when executed; not a test of it. empirical_study: a registered test of a proposition. |
| `demonstration` (Demonstration) | Data | The demonstration this experiment belongs to, e.g. 'Demonstration 1: Agentic Routinization and Adaptive Repertoire'. Blank for platform validation. |
| `research_question` (Research Question) | Small Text |  |
| `theoretical_mechanism` (Theoretical Mechanism) | Small Text |  |
| `focal_construct` (Focal Construct) | Link → `EORL Construct` | V2 section 21 (Theory Compiler): the focal theoretical construct this experiment is designed to test. Optional and purely a link -- the structured wizard itself is a later milestone. |
| `primary_outcomes` (Primary Outcomes) | Small Text |  |
| `pre_registered_hypotheses` (Pre-Registered Hypotheses / Competing Predictions) | Text |  |
| `architecture_a` (Architecture A) | Link → `EORL Architecture` | Required unless an 'architecture' factor is defined below. Also used as the fallback architecture for any factorial cell that doesn't itself define an 'architecture' factor. |
| `architecture_b` (Architecture B (optional second level)) | Link → `EORL Architecture` |  |
| `regime_shift` (Regime Shift) | Link → `EORL Regime Shift` | Fallback regime shift for any factorial cell that doesn't itself define a 'regime_shift' factor. |
| `episode_count` (Episodes Per Run) | Int |  |
| `repetitions_per_cell` (Repetitions Per Cell) | Int |  |
| `seed_strategy` (Seed Strategy) | Select (paired / independent) | paired: every cell in the same repetition shares a seed, so they see the identical exogenous scenario stream (spec section 18). independent: each cell gets its own seed offset. |
| `actor_engine` (Actor Engine) | Select (as_configured / scripted_deterministic / bounded_rational / llm) | Chosen independently of the organizational architecture. as_configured uses each Agent Template's own Model Profile. |
| `base_seed` (Base Seed) | Int |  |
| `factors` (Factors) | Table → `EORL Experiment Factor` |  |
| `model_replication_strategy` (Model Replication Strategy) | Small Text |  |
| `stopping_rules` (Stopping Rules) | Small Text |  |
| `notes` (Notes) | Text |  |
| `interpretation_combination` (Interpretation Combination Rule) | Select (AND / OR / weighted / separate) | How the registered interpretation labels of this experiment's Analysis Plans combine into one verdict (eorl_lab.analysis.interpretation.combine). |
