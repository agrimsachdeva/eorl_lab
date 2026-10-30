# EORL Lab

**Executable Organizational Routine Laboratory.**

EORL Lab is a Frappe/ERPNext app for running controlled experiments on
organizational structure itself, against a persistent ERPNext company
rather than a toy simulation. Teams of agents (scripted or LLM-backed)
act under real authority constraints, tool access, memory, and
communication policies. Their actions — purchase orders, receipts,
invoices, payments — are consequential, and they leave a queryable,
event-sourced trace behind.

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
  bar at the top of any page, or go straight to the
  [API Reference](reference/index.md) / [DocType Reference](doctypes/index.md).
- **Want the history of what's been built and why?** See
  [Project History](history/sota-roadmap.md) for both specs this project
  tracks against, plus a milestone-by-milestone record of what shipped.

## What's actually real right now

This documentation describes the system as it exists today, not
aspirationally. Where something named in either spec isn't built yet,
the relevant guide page says so directly. The site is generated from
(and kept in sync with) `SOTA_ROADMAP.md`, so the two shouldn't
contradict each other — if you spot a place where they do, that's a
documentation bug worth filing.
