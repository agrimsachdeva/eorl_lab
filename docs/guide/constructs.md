# Constructs & Theory

> V2 spec, section 20: *"Create a reusable library connecting theory
> to implementation."*

`EORL Construct` is a standalone DocType (not a child table) holding:
`construct_name`, `theoretical_definition`, `level_of_analysis`,
`source_citations`, `computational_definition`, `manipulation_strategy`,
`measurement_function`, `required_events`, `validity_notes`, `version`.

`measurement_function` is a dotted Python path. Call
`EORLConstruct.resolve_measurement_function()` to get back the actual
callable:

```python
construct = frappe.get_doc("EORL Construct", "Routine coherence")
fn = construct.resolve_measurement_function()   # -> eorl_lab.analysis.coherence.actor_continuity
value = fn(events)
```

If `measurement_function` is blank, this raises `NotImplementedError`
— loudly, rather than silently claiming a capability that doesn't
exist.

## The 8 initial constructs (seeded on install)

| Construct | Measurement function | Status |
|---|---|---|
| Routine coherence | `eorl_lab.analysis.coherence.actor_continuity` | **Implemented** |
| Adaptive repertoire | `eorl_lab.analysis.repertoire.viable_path_entropy` | **Implemented** |
| Centralization | — | Not implemented: no authority-concentration (HHI) metric exists yet |
| Specialization | — | Not implemented: no actor-task-entropy/tool-breadth metric exists yet |
| Formalization | — | Not implemented: no hard/soft-rule aggregation metric exists yet |
| Information asymmetry | — | Not implemented, and no asymmetry condition is even built to measure yet (every actor sees the same public case fields) |
| Hierarchy | — | Not implemented: no approval/assignment-depth metric exists yet |
| Transactive memory | — | Not implemented at all — no expertise-belief modeling exists anywhere in the system (`shared` memory remains unbuilt) |

This table is intentionally blunt. The registry is only useful as a
truthful map of theory-to-implementation as it stands today — see each
construct's `validity_notes` field for the full explanation of what's
missing and why.

## Linking an experiment to a construct

`EORL Experiment.focal_construct` is an optional `Link` to `EORL
Construct`. `validate_experiment` checks it resolves to a real
construct if set. This is also the first input the Theory Compiler
wizard (see [Using the Front End](front-end.md)) asks for when
scaffolding a new experiment from a theory.

## Full field reference

See the generated [`EORL Construct` DocType page](../doctypes/eorl_construct.md)
for the complete field list.
