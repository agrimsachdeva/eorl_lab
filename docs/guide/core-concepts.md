# Core Concepts (Five Layers)

EORL's design (the V2 spec's framing) splits the system into five
layers. Every DocType and module in this project belongs to one of
them:

| Layer | What it represents | Key DocTypes / modules |
|---|---|---|
| **Environment** | Exogenous scenario state — demand, suppliers, hidden ground truth, regime shifts | `eorl_lab.scenarios.procurement`, `EORL Regime Shift` |
| **Organization** | Authority, communication policy, process grammar, task assignment | `EORL Tool Policy`, `EORL Communication Policy`, `EORL Process Grammar`, `EORL Task Assignment`, `eorl_lab.runtime.authority` |
| **Actors** | Persistent identities with a role, a model provider, a memory profile, a tool policy | `EORL Agent Template`, `EORL Model Profile`, `EORL Memory Profile` |
| **Process** | What actually happened — the real ERP actions, the event trace, the paths those actions trace out | `EORL Event`, `EORL Episode`, `eorl_lab.analysis.paths` |
| **Science** | Experimental design and inference — constructs, factors, replications, branches, metrics | `EORL Experiment`, `EORL Experiment Factor`, `EORL Construct`, `EORL Branch`, `eorl_lab.analysis.*` |

## The core loop

Every episode follows the same shape, regardless of architecture:

1. **Environment** generates a case (`generate_case`) — deterministic
   given `(seed, episode, regime_shift)`, with a `case_hash` that lets
   two runs prove they saw byte-identical input.
2. For each actor's turn, the **orchestrator** builds a `ModelRequest`
   containing the actor's role, the case's *public* fields only (never
   hidden ground truth — see [Model Providers](model-providers.md)),
   what it's already observed this turn, and retrieved memory.
3. The actor's **provider** (scripted or a real model) returns a
   decision: one tool to call, with arguments.
4. The **authority firewall** (`eorl_lab.runtime.authority.evaluate`)
   checks that decision against the actor's `EORL Tool Policy` —
   hard constraints block outright; soft rules are logged but never
   block.
5. If allowed, the tool actually executes against real ERPNext state.
   The **event log** records every step of this — request, response,
   decision, authorization, execution, before/after state.
6. The actor repeats until it decides to stop (or hits the step
   safety cap), then the next actor (if any) takes its turn.

## Two coordination architectures

- **Specialist/handoff**: four role-bound actors, each with its own
  restricted tool policy, explicitly handing off to the next stage.
  Bounded discretion, explicit structure.
- **Broad autonomy**: one actor walks the entire procure-to-pay chain
  itself. Zero handoffs, by construction — "fewer mandatory handoffs,
  greater actor continuity" isn't a different policy, it's a structural
  consequence of this architecture.

Both run through the exact same tool functions, authority firewall, and
event log — see [Architectures & Agents](architectures-and-agents.md).

## Ground truth is hidden, by design

The environment's `latent_ground_truth` (supplier quality/delivery
probability, price) is never shown to an agent — not in a prompt, not
in a scripted policy's visible inputs. Agents only ever learn it by
calling a sensing tool (`inspect_received_goods`) whose *result* is
drawn from that ground truth. This is enforced at the provider level
for LLM-backed agents (`OpenAICompatibleProvider._public_case` strips
it before building a prompt) and is what makes the system's process
variety genuinely environment-driven rather than scripted.
