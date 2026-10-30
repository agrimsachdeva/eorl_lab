# EORL Regime Shift

| Field | Type | Description |
|---|---|---|
| `shift_name` (Shift Name) | Data |  |
| `trigger_episode` (Trigger Episode) | Int | The shift is in effect starting at this episode number (inclusive) for every subsequent episode in the run. |
| `shift_type` (Shift Type) | Select (abrupt / gradual) |  |
| `hidden_from_agents` (Hidden From Agents) | Check | When checked (the default, and the only mode implemented so far), the shift changes environmental parameters only -- agents are never told a shift occurred, per spec section 2.4. |
| `description` (Description) | Small Text |  |
| `expected_observable_change` (Expected Observable Change) | Small Text |  |
| `parameter_delta_json` (Parameter Delta (JSON)) | Code | Currently only the 'qty_multiplier' key is read by the scenario generator (spec section 11's demand_distribution, concretely a demand shock). Other parameter deltas (supplier reliability reversal, exception-family changes, etc.) arrive with the full Scenario Studio generator. |
