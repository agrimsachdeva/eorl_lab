# Getting Started

## Prerequisites

EORL Lab is a Frappe app that runs inside an existing Frappe/ERPNext
bench, alongside a real ERPNext company — procurement scenarios are
built against actual `Item`, `Supplier`, `Purchase Order` /
`Purchase Receipt` / `Purchase Invoice` / `Payment Entry` documents.
You'll need:

- A working Frappe bench with ERPNext installed on some site
- The `eorl_lab` app installed on that site
- For LLM-backed agents (optional): a reachable OpenAI-compatible
  inference endpoint (self-hosted vLLM/TGI/Ollama, or a hosted API) and
  an API key stored in `site_config.json` — **never** in a DocType
  field or in version control (see [Model Providers](model-providers.md))

## Installing the app

```bash
bench get-app eorl_lab <repo-url>
bench --site <your-site> install-app eorl_lab
bench --site <your-site> migrate
```

`bench migrate` also runs `eorl_lab.patches.v1_seed_initial_constructs`,
which seeds the [Construct Registry](constructs.md) with its 8 initial
entries. No manual seeding step needed.

## The fastest path to a real run

If you just want to see the system do something, the lowest-ceremony
entry point is `eorl_lab.runtime.orchestrator.run_demo_episode`:

```python
import frappe
from eorl_lab.runtime.orchestrator import run_demo_episode

# Needs one EORL Agent Template (with its own Model Profile + Tool
# Policy already set up) to exist first.
result = run_demo_episode("Your Agent Template Name", seed=42)
print(result["outcome"])
```

For anything beyond a single actor's single decision, use
`run_architecture` instead — see [Architectures & Agents](architectures-and-agents.md),
then [Building an Experiment](building-an-experiment.md) for the full
researcher workflow: Experiment → factorial design → launch → compare.

## Using the desk front end

Once the app is installed, open `/app/eorl-lab` on your site. That's
the EORL Lab home page, with links to every studio/monitoring page and
every configuration DocType. See [Using the Front End](front-end.md)
for a tour.
