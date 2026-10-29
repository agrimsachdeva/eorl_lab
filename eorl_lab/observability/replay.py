import frappe

from eorl_lab.api.metrics import compute_run_metrics
from eorl_lab.observability.exporter import case_hashes_for_run, run_initialized_payload
from eorl_lab.runtime.orchestrator import run_architecture


def reproduce_run(run_name: str) -> dict:
	"""Milestone 8: launches a NEW run from an existing run's own
	recorded configuration (architecture, seed, regime shift, episode
	count -- read back from its architecture_snapshot_json and its own
	run_initialized event, never asked of the caller), then verifies
	reproduction by comparing the new run's per-episode scenario-case
	hashes and computed metrics against the original. Never modifies
	the original run (spec section 19: "Never modify the source run").

	Honest limitation: only works for runs launched via run_architecture
	(Milestone 5+) -- their architecture_snapshot_json carries the
	architecture's own name. Runs from run_demo_episode (M2) or
	run_specialist_routine (M3/M4) don't carry enough configuration to
	look up an architecture by name, and this raises a clear error for
	them rather than guessing."""

	original = frappe.get_doc("EORL Run", run_name)
	architecture_snapshot = frappe.parse_json(original.architecture_snapshot_json or "{}")
	architecture_name = architecture_snapshot.get("name")
	if not architecture_name:
		frappe.throw(
			f"Cannot reproduce {run_name}: no architecture name recorded in its snapshot "
			"(it was likely launched via run_demo_episode or run_specialist_routine, not "
			"run_architecture, and doesn't carry enough configuration to replay)."
		)

	init_payload = run_initialized_payload(run_name)
	episode_count = init_payload.get("episode_count") or 1
	regime_shift_name = init_payload.get("regime_shift")

	reproduction = run_architecture(
		architecture_name,
		seed=original.run_seed,
		episode_count=episode_count,
		regime_shift=regime_shift_name,
	)

	original_hashes = case_hashes_for_run(run_name)
	new_hashes = case_hashes_for_run(reproduction["run"])
	scenario_stream_matches = bool(original_hashes) and original_hashes == new_hashes

	original_metrics = compute_run_metrics(run_name)["metrics"]
	new_metrics = compute_run_metrics(reproduction["run"])["metrics"]

	mismatched_metrics = []
	for key, value in original_metrics.items():
		if key not in new_metrics:
			continue
		other = new_metrics[key]
		if isinstance(value, (int, float)) and isinstance(other, (int, float)):
			if abs(value - other) > 1e-9:
				mismatched_metrics.append(key)
		elif value != other:
			mismatched_metrics.append(key)

	return {
		"original_run": run_name,
		"reproduction_run": reproduction["run"],
		"scenario_stream_matches": scenario_stream_matches,
		"metrics_match": not mismatched_metrics,
		"mismatched_metrics": mismatched_metrics,
		"original_status": original.status,
		"reproduction_status": reproduction["outcome"]["success"],
	}
