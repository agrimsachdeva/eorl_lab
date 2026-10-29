from typing import List, Optional

from eorl_lab.analysis.repertoire import concentration_in_top_k, novel_viable_paths_after_shock
from eorl_lab.analysis.sequence import sequence_entropy

PRE_PHASES = ("warmup", "stable")
POST_PHASES = ("shock", "recovery")


def _pre_post(performance_by_episode: List[float], phases: List[str]):
	pre = [p for p, ph in zip(performance_by_episode, phases) if ph in PRE_PHASES]
	post = [p for p, ph in zip(performance_by_episode, phases) if ph in POST_PHASES]
	return pre, post


def immediate_post_shock_drop(performance_by_episode: List[float], phases: List[str]) -> float:
	"""Mean pre-shock performance minus performance at the first
	post-shock episode. Positive = performance dropped."""
	pre, post = _pre_post(performance_by_episode, phases)
	if not pre or not post:
		return 0.0
	return (sum(pre) / len(pre)) - post[0]


def episodes_to_recover(
	performance_by_episode: List[float], phases: List[str], threshold_fraction: float = 0.9
) -> Optional[int]:
	"""Episodes (0-indexed offset from the first post-shock episode)
	until performance first reaches threshold_fraction of the pre-shock
	mean. None if it never recovers within the observed episodes, or if
	there's no pre-shock baseline to recover toward."""
	pre, post = _pre_post(performance_by_episode, phases)
	if not pre or not post:
		return None
	target = threshold_fraction * (sum(pre) / len(pre))
	for offset, perf in enumerate(post):
		if perf >= target:
			return offset
	return None


def area_under_recovery_curve(performance_by_episode: List[float], phases: List[str]) -> float:
	"""Sum of the performance deficit (pre-shock mean minus actual) over
	every post-shock episode. Smaller is better; 0 means immediate full
	recovery (or no drop at all)."""
	pre, post = _pre_post(performance_by_episode, phases)
	if not pre:
		return 0.0
	pre_mean = sum(pre) / len(pre)
	return sum(max(pre_mean - p, 0.0) for p in post)


def post_shock_error_rate(performance_by_episode: List[float], phases: List[str]) -> float:
	_, post = _pre_post(performance_by_episode, phases)
	if not post:
		return 0.0
	return 1.0 - (sum(post) / len(post))


def viable_new_path_discovery_rate(episode_paths, outcomes, phases: List[str]) -> float:
	"""Novel viable paths per post-shock episode (spec section 17.3's
	"rate of viable new-path discovery")."""
	post_count = sum(1 for ph in phases if ph in POST_PHASES)
	if not post_count:
		return 0.0
	return novel_viable_paths_after_shock(episode_paths, outcomes, phases) / post_count


def change_in_sequence_entropy(episode_paths: List[List[str]], phases: List[str]) -> float:
	pre_paths = [p for p, ph in zip(episode_paths, phases) if ph in PRE_PHASES]
	post_paths = [p for p, ph in zip(episode_paths, phases) if ph in POST_PHASES]
	return sequence_entropy(post_paths) - sequence_entropy(pre_paths)


def change_in_path_concentration(episode_paths, outcomes, phases: List[str], k: int = 1) -> float:
	pre = [(p, o) for p, o, ph in zip(episode_paths, outcomes, phases) if ph in PRE_PHASES]
	post = [(p, o) for p, o, ph in zip(episode_paths, outcomes, phases) if ph in POST_PHASES]
	pre_paths, pre_outcomes = (list(x) for x in zip(*pre)) if pre else ([], [])
	post_paths, post_outcomes = (list(x) for x in zip(*post)) if post else ([], [])
	return concentration_in_top_k(post_paths, post_outcomes, k=k) - concentration_in_top_k(pre_paths, pre_outcomes, k=k)
