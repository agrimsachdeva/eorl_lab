"""Attribute-level path coherence, metric `path_coherence_v1`
(submission-day plan section 4).

The Milestone 7 continuity measures (actor, functional, stage) each look
at one attribute of an action. This module represents every action as
an attribute vector and measures coherence on each attribute separately
and as a composite:

    actor, role, stage, object_type, counterparty (supplier or customer),
    exception_state, tool_family, decision_domain

Coherence of attribute k in one episode is the share of consecutive
action pairs whose value of k is the same. Pairs where either value is
missing are skipped. The run-level value is the mean over episodes that
have at least one scorable pair, so long and short episodes count
equally and no pair spans two episodes (the Milestone 7 flat measures do
count the pair across an episode boundary). The composite is the
unweighted mean of the attribute values that could be computed.

Correspondence to Kim et al. The idea that a path is coherent when
consecutive actions share attributes (who acts, on what object, in which
functional domain), and that coherence should be measured separately by
attribute rather than only by actor, follows the attribute-level framing
cited in the proposal. The specific formula here (pairwise agreement of
adjacent actions, averaged within episode, unweighted composite) is an
EORL operationalization. It has not been checked line by line against
the paper's own estimator, and any difference in weighting, distance
function or normalization should be read as an adaptation. The version
string changes if the formula does.
"""
from typing import Dict, List, Optional

from eorl_lab.analysis.paths import extract_canonical_events, scoped_events

PATH_COHERENCE_VERSION = "path_coherence_v1"

ATTRIBUTES = (
	"actor", "role", "stage", "object_type", "counterparty",
	"exception_state", "tool_family", "decision_domain",
)


def _pair_agreement(values: List[Optional[str]]) -> Optional[float]:
	scored = [(a, b) for a, b in zip(values, values[1:]) if a is not None and b is not None]
	if not scored:
		return None
	return sum(1 for a, b in scored if a == b) / len(scored)


def _group_by_episode(canonical) -> List[list]:
	groups, current, key = [], [], object()
	for e in canonical:
		if e.episode != key:
			if current:
				groups.append(current)
			current, key = [], e.episode
		current.append(e)
	if current:
		groups.append(current)
	return groups


def attribute_coherence(events: List[dict], scope: str = "all_actions", stage_map: Optional[dict] = None) -> Dict[str, Optional[float]]:
	"""{attribute: coherence in [0, 1] or None} plus "composite"."""
	canonical = scoped_events(events, scope, stage_map) if scope != "all_actions" else extract_canonical_events(events, stage_map)
	episodes = _group_by_episode(canonical)

	result: Dict[str, Optional[float]] = {}
	for attribute in ATTRIBUTES:
		per_episode = [_pair_agreement([e.attributes.get(attribute) for e in ep]) for ep in episodes]
		per_episode = [v for v in per_episode if v is not None]
		result[attribute] = (sum(per_episode) / len(per_episode)) if per_episode else None

	available = [v for v in result.values() if v is not None]
	result["composite"] = (sum(available) / len(available)) if available else None
	return result
