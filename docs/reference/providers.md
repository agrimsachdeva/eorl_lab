# Providers

The run loop never hard-codes a model — every actor resolves its own
provider from its `EORL Model Profile` via
`eorl_lab.providers.factory.get_provider_for_agent`.

::: eorl_lab.providers.base

::: eorl_lab.providers.factory

::: eorl_lab.providers.deterministic

::: eorl_lab.providers.openai_compatible
