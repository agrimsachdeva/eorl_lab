import frappe

from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.providers.openai_compatible import OpenAICompatibleProvider

# "anthropic" is a real EORL Model Profile option (spec section 8.1
# anticipates multiple provider engines) but has no implementation yet.
_UNIMPLEMENTED_PROVIDERS = {"anthropic"}


def get_provider_for_agent(agent):
	"""SOTA Milestone 3: resolves the actual model provider from this
	actor's OWN `EORL Model Profile`, instead of the run loop
	hard-coding `DeterministicProvider()` once for every actor in the
	run regardless of what each agent template actually asked for (the
	entire system ran on a scripted policy through SOTA Milestone 2
	despite the provider abstraction existing since Milestone 2's
	vertical slice). Different actor slots in the same run can now
	genuinely use different providers."""
	model_profile = frappe.get_doc("EORL Model Profile", agent.model_profile)
	if not model_profile.enabled:
		frappe.throw(f"EORL Model Profile {model_profile.name!r} is disabled.")

	provider = model_profile.provider
	if provider == "deterministic":
		return DeterministicProvider()
	if provider == "openai_compatible":
		return OpenAICompatibleProvider(model_profile)
	if provider in _UNIMPLEMENTED_PROVIDERS:
		raise NotImplementedError(
			f"EORL Model Profile provider {provider!r} is not implemented yet "
			"(requires a later milestone's provider class)."
		)
	raise ValueError(f"Unknown model provider: {provider!r}")
