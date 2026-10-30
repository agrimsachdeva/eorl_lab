# API Reference

Every page in this section is generated directly from the docstrings in
`eorl_lab`'s own source code (via [mkdocstrings](https://mkdocstrings.github.io/)).
If a description here looks wrong, the fix belongs in the code's
docstring, not in this file.

Module groups:

| Section | What it covers |
|---|---|
| [Runtime](runtime.md) | The episode loop, actor-turn loop, authority firewall, counterfactual branching |
| [Providers](providers.md) | `ModelProvider` interface, `DeterministicProvider`, `OpenAICompatibleProvider`, per-agent provider resolution |
| [Memory](memory.md) | `MemoryStore` interface and all five local backends |
| [ERP Tools](erp.md) | The semantic ERP adapter — the actual tool functions agents call |
| [Organization](organization.md) | Agent-chosen communication (`message_agent`) and turn control (`finish_turn`) |
| [Analysis](analysis.md) | Process-mining and theory metrics: coherence, repertoire, sequence, recovery, networks |
| [Scenarios](scenarios.md) | The deterministic, seed-driven procurement scenario generator |
| [Observability](observability.md) | The append-only event log and experiment context |
| [Whitelisted API](api.md) | The `eorl_lab.api.*` functions the front end (and any external caller) actually hits |

For *what the system's DocTypes look like* (fields, link targets,
options), see the [DocType Reference](../doctypes/index.md) instead —
DocTypes aren't plain Python classes, so they're documented separately
from this section.
