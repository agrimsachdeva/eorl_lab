# Memory

Every actor's memory goes through the same `MemoryStore` interface
regardless of backend, so the orchestrator can log `memory_query` /
`memory_retrieval` / `memory_write` events uniformly. See the
[Memory Types guide](../guide/memory-types.md) for when to use which.

::: eorl_lab.memory.base

::: eorl_lab.memory.factory

::: eorl_lab.memory.none

::: eorl_lab.memory.recent

::: eorl_lab.memory.episodic

::: eorl_lab.memory.semantic

::: eorl_lab.memory.procedural
