# EORL Construct

| Field | Type | Description |
|---|---|---|
| `construct_name` (Construct Name) | Data |  |
| `version` (Version) | Data |  |
| `level_of_analysis` (Level of Analysis) | Select (actor / dyad / group / organization / process) |  |
| `theoretical_definition` (Theoretical Definition) | Text |  |
| `source_citations` (Source Citations) | Small Text |  |
| `computational_definition` (Computational Definition) | Text |  |
| `manipulation_strategy` (Manipulation Strategy) | Text |  |
| `measurement_function` (Measurement Function) | Data | Dotted Python path to the real function that computes this construct (e.g. 'eorl_lab.analysis.coherence.actor_continuity'), resolved by EORLConstruct.resolve_measurement_function(). Leave blank if not implemented yet -- say so in Validity Notes instead of guessing. |
| `required_events` (Required Event Types) | Small Text | Comma-separated EORL Event.event_type values the measurement function needs present in a run's trace to compute this construct. |
| `validity_notes` (Validity Notes) | Text |  |
