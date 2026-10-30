# EORL Lab

**Executable Organizational Routine Laboratory.**

EORL Lab is a Frappe/ERPNext app for running controlled experiments on
*organizational structure itself* — not on a simulated toy environment,
but against a real, persistent ERPNext company. Teams of agents
(scripted or LLM-backed) act under real authority constraints, real
tool access, real memory, and real communication policies, performing
consequential actions (purchase orders, receipts, invoices, payments)
that leave a real, queryable, event-sourced trace behind.

> EORL is a laboratory for executable organizing: persistent enterprise
> state, consequential action, explicit organizational structure,
> configurable process discretion, longitudinal memory, native process
> traces, matched-history counterfactuals, and theory-linked
> experimental constructs.

## Where to start

- **New to the project?** Start with [Getting Started](guide/getting-started.md),
  then [Core Concepts](guide/core-concepts.md) for the five-layer model
  everything else builds on.
- **Want to run an experiment?** [Building an Experiment](guide/building-an-experiment.md)
  walks through the whole researcher workflow end to end.
- **Looking for a specific function, class, or DocType?** Use the search
  bar (top of every page) or jump straight to the
  [API Reference](reference/index.md) / [DocType Reference](doctypes/index.md).
- **Want the history of what's been built and why?** See
  [Project History](history/sota-roadmap.md) — both specs this project
  tracks against, and an honest record of what's real vs. still a gap.

## What's actually real right now

This documentation describes the system **as it exists today**, not
aspirationally. Where something named in either spec isn't built yet,
the relevant guide page says so explicitly, the same way
`SOTA_ROADMAP.md` does — this site is generated from (and kept in sync
with) that same honesty standard.
