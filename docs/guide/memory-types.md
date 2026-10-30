# Memory Types

Set via `EORL Memory Profile.local_backend`, resolved by
`eorl_lab.memory.factory.get_memory_store`. Every backend implements
the same `MemoryStore` interface (`retrieve` / `write` / `reset`), so
the orchestrator logs `memory_query` / `memory_retrieval` /
`memory_write` events identically regardless of which one is active —
memory choice is a real experimental manipulation, not hidden
convenience state.

| Backend | What it stores | Use it when |
|---|---|---|
| `none` | Nothing — reads always empty, writes discarded | You want a no-memory baseline condition |
| `recent` | Pure recency ranking (a thin specialization of `episodic` with `recency_weight=1.0`) | You want "what did I just do" with no outcome weighting |
| `episodic` | One row per episode, ranked by a weighted blend of recency + outcome | You want the actor to recall and repeat successful past actions — this is what routinization (Milestone 4) is built on |
| `semantic` | **Consolidated facts** about a stable subject (e.g. a supplier), upserted — one row per subject, not one per episode | You want "what do I believe about X", accumulated across many episodes, not a growing log |
| `procedural` | A single reinforced **habit** per actor — repeating the same successful action strengthens it; a different action resets it | You want to model habit formation/extinction, not fact accumulation |
| `shared` | *Not implemented* (V2 §32.2 calls it P2) | — |
| `vector` | *Not implemented* (needs an embedding-model profile) | — |

## Semantic vs. procedural vs. episodic — the actual distinction

These three are easy to blur, so it's worth being precise:

- **Episodic** keeps a *trace*: every observation, kept individually,
  ranked for retrieval. Growing, not consolidating.
- **Semantic** keeps *facts*: "Bloomington Dairy has succeeded in 8/9
  observations" — one row per subject, continuously updated. The
  subject is derived from the action string itself
  (`"ordered_from:X"` → `"supplier:X"`), **not** from the per-episode
  `case_summary` the orchestrator writes by default — that's a fresh
  case id every episode, not a stable subject to generalize about.
- **Procedural** keeps a *habit*: "what do I currently tend to do" —
  exactly one row per `(run, actor, domain)`, whose `salience` climbs
  toward 1.0 on repetition and resets to a fresh, weak value the moment
  a genuinely different action is taken. It never blends two different
  habits together.

## Using memory directly

```python
from eorl_lab.memory.factory import get_memory_store

profile = frappe.get_doc("EORL Memory Profile", "My Profile")
store = get_memory_store(profile)

store.write({
    "run": run_name, "episode": episode_name, "actor": agent_name,
    "domain": "procurement", "case_summary": "...", "action": "ordered_from:X",
    "outcome": "success", "success": 1, "salience": 1.0, "payload_json": "{}",
})

store.retrieve(run=run_name, actor=agent_name, domain="procurement", k=3)
```

In practice you don't call this directly — the orchestrator's
`_retrieve_memory` / `_write_memory` do it for you once an actor's
`EORL Agent Template.memory_profile` is set.
