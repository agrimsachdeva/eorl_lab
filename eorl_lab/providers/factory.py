import frappe

from eorl_lab.providers.bounded_rational import BoundedRationalProvider
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.providers.openai_compatible import OpenAICompatibleProvider

# "anthropic" is a real EORL Model Profile option (spec section 8.1
# anticipates multiple provider engines) but has no implementation yet.
_UNIMPLEMENTED_PROVIDERS = {"anthropic"}


# Submission-day plan section 9: the actor engine is a design factor of
# its own, chosen independently of the organizational architecture.
ACTOR_ENGINES = ("as_configured", "scripted_deterministic", "bounded_rational", "llm")


def engine_type_of(provider_name: str) -> str:
	return {"deterministic": "scripted_deterministic", "bounded_rational": "bounded_rational"}.get(provider_name, "llm")


def get_provider_for_agent(agent, engine_override: str = None):
	"""SOTA Milestone 3: resolves the actual model provider from this
	actor's OWN `EORL Model Profile`, instead of the run loop
	hard-coding `DeterministicProvider()` once for every actor in the
	run regardless of what each agent template actually asked for (the
	entire system ran on a scripted policy through SOTA Milestone 2
	despite the provider abstraction existing since Milestone 2's
	vertical slice). Different actor slots in the same run can now
	genuinely use different providers.

	`engine_override` replaces the configured engine for every actor of a
	run without touching the architecture: "scripted_deterministic" and
	"bounded_rational" need no model profile at all; "llm" requires the
	agent's own profile to be a language-model provider and refuses to
	quietly fall back to a scripted one."""
	if engine_override and engine_override not in ACTOR_ENGINES:
		frappe.throw(f"Unknown actor engine {engine_override!r}; use one of {ACTOR_ENGINES}.")
	if engine_override == "scripted_deterministic":
		return DeterministicProvider()
	if engine_override == "bounded_rational":
		return BoundedRationalProvider()

	model_profile = frappe.get_doc("EORL Model Profile", agent.model_profile)
	if engine_override == "llm" and model_profile.provider in ("deterministic", "bounded_rational"):
		frappe.throw(
			f"actor_engine='llm' but agent {agent.name!r} is bound to the non-generative profile "
			f"{model_profile.name!r}; bind a language-model profile instead."
		)
	if not model_profile.enabled:
		frappe.throw(f"EORL Model Profile {model_profile.name!r} is disabled.")

	provider = model_profile.provider
	if provider == "deterministic":
		return DeterministicProvider()
	if provider == "bounded_rational":
		return BoundedRationalProvider()
	if provider == "openai_compatible":
		return OpenAICompatibleProvider(model_profile)
	if provider in _UNIMPLEMENTED_PROVIDERS:
		raise NotImplementedError(
			f"EORL Model Profile provider {provider!r} is not implemented yet "
			"(requires a later milestone's provider class)."
		)
	raise ValueError(f"Unknown model provider: {provider!r}")
