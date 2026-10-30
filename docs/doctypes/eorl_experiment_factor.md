# EORL Experiment Factor

*Child table.*

| Field | Type | Description |
|---|---|---|
| `factor_name` (Factor Name) | Data | e.g. 'coordination_structure'. Every row sharing the same factor_name is one LEVEL of that factor; the experiment's cell count is the product of each distinct factor_name's level count. |
| `level_label` (Level Label) | Data | Human-readable label for this level, e.g. 'Specialist Handoff'. |
| `factor_type` (Factor Type) | Select (architecture / regime_shift) | What this level actually varies at launch. Limited today to the two independent knobs run_architecture() exposes -- varying model/memory profile per factor would require per-combination EORL Architecture documents (actor_slots bind specific agent templates), so model/memory variation is expressed by making 'architecture' itself the factor. |
| `architecture` (Architecture) | Link → `EORL Architecture` | Set when factor_type = architecture. |
| `regime_shift` (Regime Shift) | Link → `EORL Regime Shift` | Set when factor_type = regime_shift. Leave blank for a 'no shift' baseline level. |
| `is_baseline` (Is Baseline Level) | Check | Marks this level as the reference level for this factor (V2 section 19's ablation framing: other levels are described relative to this one). |
