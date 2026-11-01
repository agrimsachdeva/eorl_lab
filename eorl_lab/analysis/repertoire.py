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


# ---------------------------------------------------------------------------
# Adaptive repertoire v2 (submission-day plan section 6). Three sets are
# kept apart: observed paths (anything that happened), viable paths
# (paths that met the declared criterion below at least once), and paths
# activated after a shock (viable paths that were actually used,
# successfully, once the environment changed). Observed variation is not
# treated as repertoire.
# ---------------------------------------------------------------------------

VIABILITY_CRITERION_V2 = "v2"
DEFAULT_UTILITY_THRESHOLD = 0.9


def episode_utility(outcome: dict) -> float:
	"""Outcome utility in [0, 1] (utility model v1). New runs record
	`utility` in the episode outcome (eorl_lab.runtime.orchestrator):
	0 for an episode that did not complete, otherwise 1 minus the share
	of received units rejected on inspection. For older outcomes without
	that field, a completed episode with a failed inspection counts 0.5
	and any other completed episode 1.0."""
	if outcome.get("utility") is not None:
		return float(outcome["utility"])
	if not outcome.get("success"):
		return 0.0
	if outcome.get("quality_passed") is False:
		return 0.5
	return 1.0


def is_viable_v2(outcome: dict, utility_threshold: float = DEFAULT_UTILITY_THRESHOLD) -> bool:
	"""Criterion v2: terminal success, no hard-policy violation, and
	utility at or above `utility_threshold`. A hard violation (a denied
	tool call) ends the episode as a failure in this orchestrator, so the
	second condition is checked through the recorded failure type as
	well as the success flag."""
	if not outcome.get("success"):
		return False
	if (outcome.get("failure_type") or "").startswith("authority_denial"):
		return False
	return episode_utility(outcome) >= utility_threshold


def adaptive_repertoire(episode_paths, outcomes, phases, utility_threshold: float = DEFAULT_UTILITY_THRESHOLD) -> dict:
	"""Every repertoire measure the plan lists. `episode_paths` should be
	a consequential-action view (eorl_lab.analysis.paths.process_path
	with scope="consequential_actions"), so a change of supplier is a
	change of path and optional reads are not."""
	paths = [tuple(p) for p in episode_paths]
	viable_flags = [is_viable_v2(o, utility_threshold) for o in outcomes]

	observed = set(paths)
	viable_counts = Counter(p for p, v in zip(paths, viable_flags) if v)
	viable_total = sum(viable_counts.values())

	result = {
		"viability_criterion": VIABILITY_CRITERION_V2,
		"utility_threshold": utility_threshold,
		"observed_path_count": len(observed),
		"viable_path_count": len(viable_counts),
		"viable_path_entropy": shannon_entropy(viable_counts),
		"viable_path_concentration": (max(viable_counts.values()) / viable_total) if viable_total else 0.0,
	}

	pre_idx = [i for i, ph in enumerate(phases) if ph in ("warmup", "stable")]
	post_idx = [i for i, ph in enumerate(phases) if ph in ("shock", "recovery")]
	if not pre_idx or not post_idx:
		return result

	pre_viable = Counter(paths[i] for i in pre_idx if viable_flags[i])
	pre_observed = {paths[i] for i in pre_idx}
	pre_modal = Counter(paths[i] for i in pre_idx).most_common(1)[0][0]
	post_observed = {paths[i] for i in post_idx}
	post_viable_episodes = [i for i in post_idx if viable_flags[i]]
	activated = {paths[i] for i in post_viable_episodes} & set(pre_viable)

	activation_latency = None
	for offset, i in enumerate(post_idx):
		if viable_flags[i] and paths[i] in pre_viable and paths[i] != pre_modal:
			activation_latency = offset
			break

	n_pre_viable = len(pre_viable)
	result.update({
		"pre_shock_repertoire_size": n_pre_viable,
		"pre_shock_repertoire_entropy": shannon_entropy(pre_viable),
		"post_shock_reuse_rate": (
			sum(1 for i in post_viable_episodes if paths[i] in pre_viable) / len(post_viable_episodes)
		) if post_viable_episodes else 0.0,
		"post_shock_novel_path_rate": sum(1 for i in post_idx if paths[i] not in pre_observed) / len(post_idx),
		"path_extinction_rate_v2": (len(set(pre_viable) - post_observed) / n_pre_viable) if n_pre_viable else 0.0,
		"repertoire_retention": (len(set(pre_viable) & post_observed) / n_pre_viable) if n_pre_viable else 0.0,
		"repertoire_activation_latency": activation_latency,
		"adaptive_repertoire_utilization": (len(activated) / n_pre_viable) if n_pre_viable else 0.0,
		"activated_after_shock_paths": len(activated),
	})
	return result
