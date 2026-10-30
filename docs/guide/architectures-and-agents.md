# Architectures & Agents

## Building blocks, bottom-up

To launch any run, you need, in this order:

1. **`EORL Model Profile`** — which provider an actor uses
   (`deterministic` or `openai_compatible`), and its connection details.
   See [Model Providers](model-providers.md).
2. **`EORL Memory Profile`** (optional — omit for no memory) — which
   local memory backend an actor uses. See [Memory Types](memory-types.md).
3. **`EORL Tool Policy`** — the actual authority firewall for one actor:
   which tools it may call (`allowed_semantic_tools`), whether it may
   submit/approve documents, message other agents, and the hard/soft
   constraint knobs (`max_write_actions_per_episode`,
   `soft_rule_large_qty_threshold`, ...).
4. **`EORL Agent Template`** — ties a role name to one Model Profile,
   one Memory Profile, one Tool Policy, and (for LLM-backed agents) the
   system prompt (`initial_system_instructions`).
5. **`EORL Architecture`** — `coordination_mode` (`specialist_handoff`
   or `broad_autonomy`) + `actor_slots` (which Agent Template fills
   which slot), optionally bound to an `EORL Communication Policy`
   and/or `EORL Process Grammar`.

## Launching a run directly

```python
from eorl_lab.runtime.orchestrator import run_architecture

result = run_architecture(
    "My Architecture",
    seed=42,
    episode_count=20,
    regime_shift="My Regime Shift",   # optional
)
print(result["outcome"], result["event_count"])
```

Every episode in the run shares the architecture's `coordination_mode`.
Per-episode outcomes are in `result["episodes"]`.

## What a Tool Policy actually enforces

`eorl_lab.runtime.authority.evaluate()` is the only thing that decides
whether a requested tool call executes — never the model, never the
prompt text. It checks, in order:

1. Is the tool in `allowed_semantic_tools`? (`TOOL_NOT_IN_POLICY` if not)
2. Is a write-tool call over `max_write_actions_per_episode`? (`WRITE_BUDGET_EXCEEDED`)
3. Does a `submit_*` tool require `may_submit_documents`? (`SUBMIT_NOT_PERMITTED`)
4. Does `message_agent` require `may_message_agents`? (`MESSAGING_NOT_PERMITTED`)
5. Otherwise: **allowed**, plus any **soft violations** (logged as a
   `soft_rule_violation` event, never blocking) — currently one
   concrete soft rule: `create_purchase_order` above
   `soft_rule_large_qty_threshold`.

## The `finish_turn` tool

Since SOTA Milestone 3, any actor (scripted or model-driven) can be
given the `finish_turn` tool in its policy's `allowed_semantic_tools`.
A model-driven actor needs this explicitly — it has no scripted
"bundle `stop=True` onto my last real action" shortcut the way
`DeterministicProvider` does, so it needs a real, authority-governed
way to decide its turn is over.
