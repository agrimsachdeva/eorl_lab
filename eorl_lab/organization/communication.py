import frappe


def message_agent(recipient_slot: str, content: str, _sender_slot: str = None, _communication_policy: str = None) -> dict:
	"""Agent-chosen communication (V2 spec section 9), distinct from the
	orchestrator-enforced structural handoffs between pipeline stages
	(eorl_lab.runtime.orchestrator._handoff). This is a tool the actor
	itself decides to call -- checked against a real EORL Communication
	Policy graph, not a hardcoded sequence -- so an actor can reach
	outside its normal handoff chain only where the policy's edges
	actually allow it.

	`_sender_slot` and `_communication_policy` are injected by the
	orchestrator (eorl_lab.runtime.orchestrator._call_tool_with_context)
	and never agent-supplied: the sender is always exactly whichever
	actor's turn it is, and the policy is whichever one is bound to the
	run's architecture -- an agent cannot forge either."""
	if not _communication_policy or not frappe.db.exists("EORL Communication Policy", _communication_policy):
		return {"delivered": False, "reason": "NO_POLICY_BOUND", "sender": _sender_slot, "recipient": recipient_slot}

	policy = frappe.get_doc("EORL Communication Policy", _communication_policy)
	edge = next(
		(e for e in policy.edges if e.from_slot == _sender_slot and e.to_slot == recipient_slot),
		None,
	)
	if not edge or not edge.allowed:
		return {
			"delivered": False,
			"reason": "NO_COMMUNICATION_EDGE",
			"sender": _sender_slot,
			"recipient": recipient_slot,
		}

	return {
		"delivered": True,
		"sender": _sender_slot,
		"recipient": recipient_slot,
		"content": content,
	}
