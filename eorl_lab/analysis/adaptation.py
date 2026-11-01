"""Behavioral adaptation to a path-invalidating shock (submission-day
plan section 5).

A demand shock changes quantities but leaves the best path where it
was, so nothing has to adapt. The supplier-quality reversal
(eorl_lab.scenarios.procurement) makes the previously dominant sourcing
choice the worse one. These functions measure what the organization did
about it, from the consequential-action paths and the per-episode
utility, without any Frappe access.
"""
from collections import Counter
from typing import List, Optional

from eorl_lab.analysis.repertoire import episode_utility, is_viable_v2

PRE_PHASES = ("warmup", "stable")
POST_PHASES = ("shock", "recovery")
STABLE_WINDOW = 3


def _split(items, phases):
	pre = [x for x, ph in zip(items, phases) if ph in PRE_PHASES]
	post = [x for x, ph in zip(items, phases) if ph in POST_PHASES]
	return pre, post


def shock_adaptation(episode_paths: List[List[str]], outcomes: List[dict], phases: List[str],
	chosen_counterparties: List[Optional[str]], stable_window: int = STABLE_WINDOW) -> dict:
	"""`chosen_counterparties[i]` is the supplier episode i ordered from
	(None if it never got that far).

	- episodes_to_first_adaptive_path: offset from the first post-shock
	  episode to the first one whose path differs from the pre-shock
	  dominant path and is viable (repertoire criterion v2). A path that
	  differs only because an exception was handled is not viable and so
	  is not adaptation. None if that never happened.
	- episodes_to_stable_new_path: offset to the first post-shock episode
	  that starts `stable_window` consecutive viable episodes on one and
	  the same path that is not the pre-shock dominant one. None if never.
	- performance_deficit: sum over post-shock episodes of (pre-shock
	  mean utility minus that episode's utility), floored at zero.
	"""
	paths = [tuple(p) for p in episode_paths]
	pre_paths, post_paths = _split(paths, phases)
	if not pre_paths or not post_paths:
		return {}
	pre_outcomes, post_outcomes = _split(outcomes, phases)
	pre_parties, post_parties = _split(chosen_counterparties, phases)

	dominant = Counter(pre_paths).most_common(1)[0][0]
	first_adaptive = next(
		(k for k, (p, o) in enumerate(zip(post_paths, post_outcomes)) if p != dominant and is_viable_v2(o)), None
	)
	stable_new = None
	for k in range(len(post_paths) - stable_window + 1):
		window = post_paths[k:k + stable_window]
		window_outcomes = post_outcomes[k:k + stable_window]
		if window[0] != dominant and all(p == window[0] for p in window) and all(is_viable_v2(o) for o in window_outcomes):
			stable_new = k
			break

	pre_utility = [episode_utility(o) for o in pre_outcomes]
	post_utility = [episode_utility(o) for o in post_outcomes]
	pre_mean = sum(pre_utility) / len(pre_utility)

	return {
		"pre_shock_dominant_path": list(dominant),
		"pre_shock_dominant_path_share": pre_paths.count(dominant) / len(pre_paths),
		"pre_shock_supplier_distribution": dict(Counter(p for p in pre_parties if p)),
		"post_shock_supplier_distribution": dict(Counter(p for p in post_parties if p)),
		"post_shock_dominant_path_share": post_paths.count(dominant) / len(post_paths),
		"episodes_to_first_adaptive_path": first_adaptive,
		"episodes_to_stable_new_path": stable_new,
		"pre_shock_mean_utility": pre_mean,
		"post_shock_mean_utility": sum(post_utility) / len(post_utility),
		"performance_deficit": sum(max(pre_mean - u, 0.0) for u in post_utility),
	}
