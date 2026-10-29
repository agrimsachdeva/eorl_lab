from collections import Counter, defaultdict
from typing import List

from eorl_lab.analysis.sequence import shannon_entropy

VIABILITY_CRITERION_VERSION = "v1"


def is_viable(outcome: dict) -> bool:
	"""Spec section 17.3: "Do not operationalize repertoire merely as the
	raw number of different paths. Define a path as viable if it
	satisfies an explicitly versioned success criterion." Criterion v1:
	the episode's own outcome.success flag. A future version might add a
	cost or cycle-time ceiling; this function's docstring is the place
	that version lives, and VIABILITY_CRITERION_VERSION is what callers
	should record alongside any metric derived from it."""
	return bool(outcome.get("success"))


def _viable_paths(episode_paths: List[List[str]], outcomes: List[dict]) -> List[tuple]:
	return [tuple(p) for p, o in zip(episode_paths, outcomes) if is_viable(o)]


def viable_unique_paths(episode_paths: List[List[str]], outcomes: List[dict]) -> set:
	return set(_viable_paths(episode_paths, outcomes))


def viable_path_entropy(episode_paths: List[List[str]], outcomes: List[dict]) -> float:
	return shannon_entropy(Counter(_viable_paths(episode_paths, outcomes)))


def repertoire_breadth_by_exception_family(
	episode_paths: List[List[str]], outcomes: List[dict], exception_families: List[str]
) -> dict:
	"""Spec section 17.3. Milestone 7 deviation: the current scenario
	generator (eorl_lab.scenarios.procurement) doesn't vary
	exception_family per episode yet -- every episode's family is
	"none" -- so on today's data this always returns a single-key dict.
	The function itself is correct and will discriminate correctly once
	exception families vary (Scenario Studio, a later milestone); this
	is not a stub pretending to work."""
	breadth = defaultdict(set)
	for path, outcome, family in zip(episode_paths, outcomes, exception_families):
		if is_viable(outcome):
			breadth[family].add(tuple(path))
	return {family: len(paths) for family, paths in breadth.items()}


def _split_by_phase(episode_paths, outcomes, phases):
	pre = [(p, o) for p, o, ph in zip(episode_paths, outcomes, phases) if ph in ("warmup", "stable")]
	post = [(p, o) for p, o, ph in zip(episode_paths, outcomes, phases) if ph in ("shock", "recovery")]
	pre_viable = {tuple(p) for p, o in pre if is_viable(o)}
	post_viable = {tuple(p) for p, o in post if is_viable(o)}
	return pre_viable, post_viable


def proportion_repertoire_reused_after_shock(episode_paths, outcomes, phases) -> float:
	"""Of the viable paths seen pre-shock, what fraction reappear
	(viably) after the shock? Undefined (returns 0.0) if nothing viable
	was seen pre-shock."""
	pre_viable, post_viable = _split_by_phase(episode_paths, outcomes, phases)
	if not pre_viable:
		return 0.0
	return len(pre_viable & post_viable) / len(pre_viable)


def novel_viable_paths_after_shock(episode_paths, outcomes, phases) -> int:
	pre_viable, post_viable = _split_by_phase(episode_paths, outcomes, phases)
	return len(post_viable - pre_viable)


def path_extinction_rate(episode_paths, outcomes, phases) -> float:
	"""Of the viable paths seen pre-shock, what fraction never reappear
	after the shock?"""
	pre_viable, post_viable = _split_by_phase(episode_paths, outcomes, phases)
	if not pre_viable:
		return 0.0
	return len(pre_viable - post_viable) / len(pre_viable)


def concentration_in_top_k(episode_paths: List[List[str]], outcomes: List[dict], k: int = 1) -> float:
	"""What fraction of viable episodes followed one of the top-k most
	common viable paths. 1.0 iff there are <=k distinct viable paths."""
	counts = Counter(_viable_paths(episode_paths, outcomes))
	total = sum(counts.values())
	if total == 0:
		return 0.0
	return sum(c for _, c in counts.most_common(k)) / total
