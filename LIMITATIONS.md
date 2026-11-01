# Limitations

What the artifact does not do at the release tag. Each item is also tracked in
`artifact_manifest.json` (`partial_capabilities`, `planned_capabilities`) and in the
"Open items" section of PROGRESS.md.

## Evidence

- No proposition of the first demonstration has been tested at its registered sample size.
  The language-model pilot is 16 runs of one routine and one scenario with one model family
  (Qwen3 27B). Its registered difference came from optional read-only calls; the
  consequential-action view now separates that out, but the pilot was registered on the
  all-action view.
- The pilot architectures differ in number of actors, tool breadth, handoffs and instruction
  wording at once. The matched-tools broad-autonomy condition removes tool breadth; actor
  count and instruction wording still differ.
- The submission-day memory and shock designs use the bounded-rational engine. They show
  the instrument producing and measuring adaptation; they say nothing about how
  language-model or human actors adapt.

## Measurement

- Attribute-level path coherence (`path_coherence_v1`) is an EORL operationalization of the
  attribute-level idea in the cited work. Its formula has not been verified against the
  paper's own estimator.
- Centralization measures authority as granted. Decision and assignment rights are recorded
  but not enforced by the authority firewall.
- Information asymmetry compares the names of observed state variables, not their values,
  and every actor still sees the same public case fields.
- Utility v1 is one minus the share of rejected units. Price, delay and rework cost are not
  modeled.
- QAP on four actors has a smallest attainable p of 1/24.

## Engineering

- One bench, one ERPNext company. Branches share the ERP ledger, so ERP aggregates such as
  stock are not comparable across branches; process-trace comparisons are.
- Queued execution uses Frappe background workers on one machine. There are no distributed
  workers.
- `anthropic` provider, `shared` and `vector` memory backends are declared but not
  implemented.
- Agents and architectures are composed in plain forms; there is no graphical Agent Studio,
  Architecture Designer or Scenario Studio.
- Model-driven runs are reproducible in configuration, scenario stream and trace, not bit
  for bit.
- Decision confidence from the language-model provider is a fixed placeholder (0.7).
- Event immutability is enforced by the application controller, not by database
  permissions.
