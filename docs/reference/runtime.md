# Runtime

The orchestrator is the actual run loop: it drives episodes, actor
turns, tool calls, authority checks, and (since SOTA Milestone 2)
counterfactual branching. The authority module is the firewall every
tool call passes through before it executes.

::: eorl_lab.runtime.orchestrator

::: eorl_lab.runtime.authority
