from typing import List


def communication_network(events: List[dict]) -> dict:
	"""{sender: {recipient: message_count}} built from agent_message_sent
	events. Milestone 7 scope: edge weights by message count only;
	richer graph metrics (centrality, density) are future work if a
	later milestone's analysis needs them -- not built speculatively now."""
	network: dict = {}
	for event in events:
		if event.get("event_type") != "agent_message_sent":
			continue
		sender = event.get("actor_slot")
		recipient = event.get("target_id")
		if not sender or not recipient:
			continue
		network.setdefault(sender, {}).setdefault(recipient, 0)
		network[sender][recipient] += 1
	return network
