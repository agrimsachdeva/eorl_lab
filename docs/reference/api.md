# Whitelisted API

Every `@frappe.whitelist()` function the front end (Run Monitor,
Experiment Studio, Trace Explorer, Compare Runs, Scientific Cockpit,
Process/Network Explorer, Adaptation View, Reproducibility Export)
actually calls. These are thin wrappers over the runtime and analysis
modules above — if you're calling EORL Lab from outside the Frappe
desk (a script, a notebook, `frappe.call`), this is the surface to use
rather than reaching into `eorl_lab.runtime` directly.

::: eorl_lab.api.runs

::: eorl_lab.api.experiments

::: eorl_lab.api.traces

::: eorl_lab.api.metrics

::: eorl_lab.api.analysis

::: eorl_lab.api.process

::: eorl_lab.api.exports

::: eorl_lab.api.queue

::: eorl_lab.api.reviewer
