"""Measurement functions for Construct Registry entries that had none
(submission-day plan section 3.1). Each takes plain data, so it can run
on an exported bundle. eorl_lab.api.metrics gathers the inputs from a
run's events and configuration snapshots.

Configuration-level constructs (centralization, tool-breadth
specialization) measure the organization as designed. Event-level
constructs (information asymmetry, task-domain specialization,
communication centralization) measure what actors actually did and saw.
"""
import math
from itertools import combinations
from typing import Dict, List, Optional

from eorl_lab.analysis.paths import _payload, extract_canonical_events
from eorl_lab.analysis.sequence import shannon_entropy
from collections import Counter

CONSTRUCT_MEASURES_VERSION = "v1"

# Keys in tool payloads that are bookkeeping rather than organizational
# state an actor learns about.
_IGNORED_KEYS = {"docstatus", "items", "content", "delivered", "recipient"}


# ---------------------------------------------------------------------------
# Information asymmetry
# ---------------------------------------------------------------------------

def observed_state_variables(events: List[dict]) -> Dict[str, set]:
	"""{actor_slot: set of state-variable names that actor observed}.
	An actor observes the keys of its own tool results and of the
	handoff or message payloads it receives."""
	seen: Dict[str, set] = {}
	for event in events:
		event_type = event.get("event_type")
		actor = event.get("actor_slot")
		if not actor or event_type not in ("tool_result", "agent_message_received"):
			continue
		payload = _payload(event)
		if event_type == "agent_message_received":
			payload = payload.get("handoff") or payload
		keys = {k for k in payload if k not in _IGNORED_KEYS and not k.startswith("_")}
		seen.setdefault(actor, set()).update(keys)
	return seen


def information_asymmetry(events: List[dict]) -> Optional[dict]:
	"""Mean pairwise Jaccard overlap of the actors' observed
	state-variable sets, and asymmetry = 1 - overlap. None with fewer
	than two actors: a single actor has no one to be asymmetric with."""
	seen = {a: s for a, s in observed_state_variables(events).items() if s}
	if len(seen) < 2:
		return None
	overlaps = []
	for a, b in combinations(sorted(seen), 2):
		union = seen[a] | seen[b]
		overlaps.append(len(seen[a] & seen[b]) / len(union) if union else 1.0)
	mean_overlap = sum(overlaps) / len(overlaps)
	return {"mean_pairwise_overlap": mean_overlap, "asymmetry": 1.0 - mean_overlap, "n_actors": len(seen)}


# ---------------------------------------------------------------------------
# Centralization (authority rights)
# ---------------------------------------------------------------------------

AUTHORITY_RIGHTS = ("decision", "approval", "assignment")


def _normalized_hhi(shares: List[float]) -> float:
	n = len(shares)
	hhi = sum(s * s for s in shares)
	if n <= 1:
		return 1.0
	return (hhi - 1.0 / n) / (1.0 - 1.0 / n)


def authority_centralization(grants: Dict[str, Dict[str, bool]]) -> Optional[dict]:
	"""`grants` = {actor: {"decision": bool, "approval": bool,
	"assignment": bool}}. For each right held by at least one actor,
	the normalized Herfindahl index of its distribution across all
	actors (0 = spread evenly, 1 = held by one actor). A single-actor
	organization is fully centralized by definition. The overall value
	is the mean over rights that are held by anyone."""
	actors = sorted(grants)
	if not actors:
		return None
	by_right = {}
	for right in AUTHORITY_RIGHTS:
		holders = [1.0 if grants[a].get(right) else 0.0 for a in actors]
		total = sum(holders)
		if total == 0:
			continue
		by_right[right] = _normalized_hhi([h / total for h in holders])
	if not by_right:
		return None
	return {"by_right": by_right, "centralization": sum(by_right.values()) / len(by_right), "n_actors": len(actors)}


# ---------------------------------------------------------------------------
# Specialization
# ---------------------------------------------------------------------------

def tool_breadth_specialization(actor_tools: Dict[str, List[str]]) -> Optional[dict]:
	"""Normalized tool breadth of actor i = |tools_i| / |union of all
	actors' tools|. Specialization = 1 - mean breadth: 0 when every
	actor holds every tool, approaching 1 as actors' tool sets shrink
	to small disjoint slices. The control tool finish_turn is excluded."""
	tools = {a: {t for t in ts if t != "finish_turn"} for a, ts in actor_tools.items()}
	union = set().union(*tools.values()) if tools else set()
	if not union:
		return None
	breadth = {a: len(ts) / len(union) for a, ts in tools.items()}
	mean_breadth = sum(breadth.values()) / len(breadth)
	return {"breadth_by_actor": breadth, "mean_normalized_breadth": mean_breadth, "specialization": 1.0 - mean_breadth}


def task_domain_entropy(events: List[dict]) -> Optional[dict]:
	"""Per actor, the Shannon entropy of the decision domains of the
	actions it actually executed, normalized by log2 of the number of
	domains observed in the run. Low values mean each actor stays in its
	own domain (specialized); 1 means every actor spreads evenly across
	all of them."""
	canonical = [e for e in extract_canonical_events(events) if e.category != "control"]
	all_domains = {e.attributes.get("decision_domain") for e in canonical} - {None}
	if len(all_domains) < 2:
		return None
	per_actor: Dict[str, Counter] = {}
	for e in canonical:
		per_actor.setdefault(e.organizational_function, Counter())[e.attributes.get("decision_domain")] += 1
	max_entropy = math.log2(len(all_domains))
	normalized = {a: shannon_entropy(c) / max_entropy for a, c in per_actor.items() if a}
	return {"by_actor": normalized, "mean_normalized_entropy": sum(normalized.values()) / len(normalized)}


# ---------------------------------------------------------------------------
# Communication centralization
# ---------------------------------------------------------------------------

def communication_centralization(network: Dict[str, Dict[str, int]]) -> Optional[float]:
	"""Freeman degree centralization of the undirected, unweighted
	message graph: sum over actors of (max degree - degree) divided by
	its maximum possible value (n - 1)(n - 2). 1 for a star, 0 when all
	actors have equal degree. None with fewer than three actors."""
	edges = set()
	for sender, targets in network.items():
		for recipient, count in targets.items():
			if count and sender != recipient:
				edges.add(frozenset((sender, recipient)))
	nodes = {n for edge in edges for n in edge}
	n = len(nodes)
	if n < 3:
		return None
	degree = {node: sum(1 for edge in edges if node in edge) for node in nodes}
	max_degree = max(degree.values())
	return sum(max_degree - d for d in degree.values()) / ((n - 1) * (n - 2))
