# Model Providers

Every actor resolves its own provider from its `EORL Model Profile`
(`eorl_lab.providers.factory.get_provider_for_agent`) — a run is never
forced onto one provider for every actor. That's been true since SOTA
Milestone 3; before that, the run loop silently hard-coded
`DeterministicProvider` for every actor regardless of what a Model
Profile's `provider` field said.

## `deterministic`

`eorl_lab.providers.deterministic.DeterministicProvider` is a
rule-based policy: one scripted decision function per role.
Deterministic given `(seed, episode, memory)`, which is what makes
reproducibility and paired-seed comparisons exact. Use this when you
want to isolate an organizational-structure manipulation from any
model-behavior variance.

It isn't purely scripted, though: since Milestone 1, the warehouse/
general-purchasing decision tree includes a ground-truth-driven branch
(`inspect_received_goods`), so the same policy can take two different
paths depending on the scenario's own hidden quality probability,
rather than a hand-toggled condition.

## `openai_compatible`

`eorl_lab.providers.openai_compatible.OpenAICompatibleProvider` talks
to a real model over the OpenAI chat-completions wire format — the
lowest common denominator most inference servers speak (vLLM, TGI,
Ollama, LM Studio, or OpenAI itself). It uses actual function/tool
calling (`tool_choice: "required"`), not JSON-in-prose parsing.

Set these fields on the `EORL Model Profile`:

| Field | Meaning |
|---|---|
| `base_url` | e.g. `http://your-host:8000/v1` |
| `model_name` | the model id the server reports under `/v1/models` |
| `api_key_reference` | the **name** of a site-config key (e.g. `qwen_api_key`) — never the key itself |
| `max_tokens` | generous headroom; a "thinking" model can spend its whole budget reasoning (see below) |
| `temperature`, `top_p` | left unset (falsy) means "don't send it" — some servers reject `top_p=0.0` outright |
| `reasoning_mode_if_supported` | set to `disabled` to send `chat_template_kwargs: {"enable_thinking": false}` (Qwen3/vLLM convention) |

Store the actual secret with:

```bash
bench --site <site> set-config qwen_api_key "<your key>"
```

That lands in `site_config.json`, which is gitignored. Never commit a
key, and never put one directly on the DocType.

### What the model actually sees

`_build_messages` constructs the prompt from:

- the case's public fields only (`item_code`, `qty`, `company`,
  `warehouse`, the case/hash ids) — `latent_ground_truth` is stripped
  before the model ever sees it
- `already_observed` — this actor's own accumulated `scratch` from
  tool results so far this turn (its only "memory" of the current
  turn; each request is stateless)
- retrieved long-term memory, if a Memory Profile is set

Tool schemas are built by introspecting each registered tool's actual
Python signature (`eorl_lab.providers.openai_compatible._tool_schema`).
Framework-injected parameters (`_case`, `_sender_slot`,
`_communication_policy`) are filtered out by name, so the model can
never see or forge them.

### A failure mode worth knowing about

Qwen3 (and similar "thinking" models) can spend their entire
`max_tokens` budget reasoning and return `finish_reason="length"` with
no tool call at all. If you see this, either raise `max_tokens`
substantially or set `reasoning_mode_if_supported = "disabled"`. Note
that disabling thinking traded away reliability in the one case this
was tested against — the model skipped straight to sensing a document
that didn't exist yet, instead of creating it first — so treat it as a
tradeoff, not a strict improvement.

## `anthropic`

A selectable `EORL Model Profile.provider` option, but not yet
implemented — resolving one raises `NotImplementedError`. The
dispatch point (`get_provider_for_agent`) is ready for it; the actual
provider class is future work.
