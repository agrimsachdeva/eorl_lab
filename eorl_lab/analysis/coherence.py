from typing import List

from eorl_lab.analysis.paths import extract_canonical_events
from eorl_lab.analysis.sequence import modal_path_share


def _switch_rate(items: List[str]) -> float:
	if len(items) < 2:
		return 0.0
	switches = sum(1 for a, b in zip(items, items[1:]) if a != b)
	return switches / (len(items) - 1)


def actor_switch_rate(events: List[dict]) -> float:
	"""Fraction of consecutive canonical-action pairs where the acting
	actor changed. 0 for a single continuous actor (broad autonomy);
	positive once more than one actor participates (specialist/handoff)."""
	return _switch_rate(actor_sequence_for(events))


def actor_sequence_for(events: List[dict]) -> List[str]:
	return [e.actor for e in extract_canonical_events(events) if e.actor]


def same_actor_transition_rate(events: List[dict]) -> float:
	return 1.0 - actor_switch_rate(events)


def actor_continuity(events: List[dict]) -> float:
	"""Named separately per spec section 17.3's "path coherence"
	construct, even though it is mathematically the complement of
	actor_switch_rate -- kept as its own function so a caller doesn't
	have to know that to use it."""
	return same_actor_transition_rate(events)


def average_actor_run_length(events: List[dict]) -> float:
	"""Mean length of consecutive same-actor runs. Equals the full
	sequence length for one continuous actor (broad autonomy); shorter
	wherever handoffs occur (specialist/handoff)."""
	actors = actor_sequence_for(events)
	if not actors:
		return 0.0
	run_lengths = []
	current = 1
	for a, b in zip(actors, actors[1:]):
		if a == b:
			current += 1
		else:
			run_lengths.append(current)
			current = 1
	run_lengths.append(current)
	return sum(run_lengths) / len(run_lengths)


def functional_switch_rate(events: List[dict]) -> float:
	functions = [e.organizational_function for e in extract_canonical_events(events) if e.organizational_function]
	return _switch_rate(functions)


def functional_continuity(events: List[dict]) -> float:
	return 1.0 - functional_switch_rate(events)


def stage_continuity(events: List[dict]) -> float:
	"""Fraction of consecutive canonical actions that stayed within the
	same process stage (spec section 17.2's eight stages)."""
	stages = [e.process_stage for e in extract_canonical_events(events)]
	return 1.0 - _switch_rate(stages)


def repeated_path_probability(episode_paths: List[List[str]]) -> float:
	"""A transparent proxy for population-level path coherence: the
	probability a randomly chosen episode followed the modal path.
	Delegates to modal_path_share rather than reimplementing identical
	arithmetic under a different name."""
	return modal_path_share(episode_paths)
