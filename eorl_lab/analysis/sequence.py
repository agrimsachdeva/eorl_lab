import math
from collections import Counter
from typing import List


def shannon_entropy(counts: Counter) -> float:
	total = sum(counts.values())
	if total == 0:
		return 0.0
	entropy = 0.0
	for c in counts.values():
		p = c / total
		entropy -= p * math.log2(p)
	return entropy


def unique_sequence_count(episode_paths: List[List[str]]) -> int:
	return len({tuple(p) for p in episode_paths})


def sequence_entropy(episode_paths: List[List[str]]) -> float:
	"""Shannon entropy (bits) over the distribution of distinct full
	episode paths. 0 iff every episode followed the identical path."""
	return shannon_entropy(Counter(tuple(p) for p in episode_paths))


def modal_path_share(episode_paths: List[List[str]]) -> float:
	"""Fraction of episodes that followed the single most common path.
	1.0 iff every episode followed the identical path."""
	counts = Counter(tuple(p) for p in episode_paths)
	if not counts:
		return 0.0
	return max(counts.values()) / sum(counts.values())


def transition_entropy(episode_paths: List[List[str]]) -> float:
	"""Entropy of step-to-step transitions, pooled across all episodes
	(not the same as sequence_entropy, which treats each whole path as
	one symbol)."""
	transitions = Counter()
	for path in episode_paths:
		for a, b in zip(path, path[1:]):
			transitions[(a, b)] += 1
	return shannon_entropy(transitions)


def directly_follows_graph(episode_paths: List[List[str]]) -> dict:
	"""{from_step: {to_step: count}}, pooled across episodes -- the
	standard process-mining primitive everything else here could in
	principle be derived from."""
	graph: dict = {}
	for path in episode_paths:
		for a, b in zip(path, path[1:]):
			graph.setdefault(a, {}).setdefault(b, 0)
			graph[a][b] += 1
	return graph
