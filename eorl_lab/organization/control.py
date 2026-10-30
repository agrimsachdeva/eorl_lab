def finish_turn() -> dict:
	"""Signals that this actor's part of the current procedure is
	complete for now; no ERP action is taken. SOTA Milestone 3: a real
	model provider needs an explicit, authority-governed way to decide
	WHEN to stop (V2 section 13's loop/deadlock safety is a ceiling, not
	a substitute for the actor's own judgment) -- the deterministic
	policy never needed this because it always bundles stop=True onto
	its own last real action, but a model choosing its actions turn by
	turn needs a dedicated no-op tool to signal "done" without pretending
	some other tool call means that. Must be explicitly present in an
	actor's EORL Tool Policy.allowed_semantic_tools like any other tool --
	it is not a backdoor around the authority firewall."""
	return {}
