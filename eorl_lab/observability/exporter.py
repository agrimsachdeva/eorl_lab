import csv
import io
import json
import os
import subprocess
import zipfile
from pathlib import Path

import frappe

from eorl_lab.analysis.paths import process_path
from eorl_lab.scenarios.procurement import generate_case

# Milestone 8 deviation from spec section 7.9's literal file list:
# "resolved_prompts/" is folded into resolved_agent_configs/ (we don't
# template prompts with runtime variable substitution yet -- the stored
# initial_system_instructions IS the resolved prompt), and
# requirements-lock.txt lists pinned frappe/erpnext/eorl_lab commits plus
# the Python version rather than a full `pip freeze` (which would mostly
# be third-party dependency noise, not the versions that actually matter
# for reproducing this app's behavior).


def _git_commit(repo_path: str) -> str:
	try:
		result = subprocess.run(
			["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, timeout=5
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except Exception:
		pass
	return "unknown"


def _app_repo_path(app_name: str) -> str:
	return os.path.join(frappe.utils.get_bench_path(), "apps", app_name)


def environment_metadata() -> dict:
	import sys

	import erpnext

	return {
		"frappe_version": frappe.__version__,
		"frappe_commit": _git_commit(_app_repo_path("frappe")),
		"erpnext_version": erpnext.__version__,
		"erpnext_commit": _git_commit(_app_repo_path("erpnext")),
		"eorl_lab_commit": _git_commit(_app_repo_path("eorl_lab")),
		"python_version": sys.version,
		"site": frappe.local.site,
	}


def case_hashes_for_run(run_name: str) -> list:
	events = frappe.get_all(
		"EORL Event",
		filters={"run": run_name, "event_type": "environment_observed"},
		fields=["payload_json"],
		order_by="sequence_no asc",
	)
	hashes = []
	for event in events:
		payload = frappe.parse_json(event.payload_json or "{}")
		hashes.append((payload.get("case") or {}).get("case_hash"))
	return hashes


def run_initialized_payload(run_name: str) -> dict:
	rows = frappe.get_all(
		"EORL Event",
		filters={"run": run_name, "event_type": "run_initialized"},
		fields=["payload_json"],
		order_by="sequence_no asc",
		limit_page_length=1,
	)
	return frappe.parse_json(rows[0].payload_json) if rows else {}


def build_run_manifest(run_doc) -> dict:
	"""Spec section 18's run manifest. Since the submission-day build it
	carries the experiment and cell that produced the run, the routine
	template, the actor engine, the outcome model, the code commit
	recorded at launch, the failure type and the runtime telemetry."""
	init_payload = run_initialized_payload(run_doc.name)
	return {
		"run_id": run_doc.name,
		"experiment_id": run_doc.get("experiment"),
		"cell_id": run_doc.get("cell_id"),
		"routine_template": run_doc.get("routine_template"),
		"actor_engine": run_doc.get("actor_engine"),
		"scenario": frappe.parse_json(run_doc.scenario_snapshot_json) if run_doc.scenario_snapshot_json else None,
		"code_commit_at_launch": run_doc.get("code_commit"),
		"failure_type": run_doc.get("failure_type"),
		"telemetry": {
			"model_calls": run_doc.get("model_calls"), "input_tokens": run_doc.get("input_tokens"),
			"output_tokens": run_doc.get("output_tokens"), "total_tokens": run_doc.get("total_tokens"),
			"retries": run_doc.get("retry_count"), "wallclock_seconds": run_doc.get("wallclock_seconds"),
			"estimated_cost": run_doc.get("total_cost"),
		},
		"seed": run_doc.run_seed,
		"status": run_doc.status,
		"started_at": str(run_doc.started_at) if run_doc.started_at else None,
		"ended_at": str(run_doc.ended_at) if run_doc.ended_at else None,
		"event_count": run_doc.event_count,
		"architecture": frappe.parse_json(run_doc.architecture_snapshot_json or "{}"),
		"agents": frappe.parse_json(run_doc.agent_snapshots_json or "{}"),
		"regime_shift": frappe.parse_json(run_doc.regime_shift_snapshot_json) if run_doc.regime_shift_snapshot_json else None,
		"episode_count_requested": init_payload.get("episode_count"),
		"coordination_mode": init_payload.get("coordination_mode"),
		"scenario_case_hashes": case_hashes_for_run(run_doc.name),
		"environment": environment_metadata(),
	}


def build_scenario_stream(run_doc) -> list:
	"""Regenerates the exact per-episode cases the run used, by calling
	the same pure generate_case() with the same (seed, regime_shift) the
	run was launched with -- not reading them back from stored events,
	so this doubles as a check that the generator is still deterministic
	for this run's inputs (spec section 18: "generated before agent
	execution and hashed so its identity across cells can be
	verified")."""
	init_payload = run_initialized_payload(run_doc.name)
	episode_count = init_payload.get("episode_count") or 1
	regime_shift_name = init_payload.get("regime_shift")

	regime_shift_payload = None
	if regime_shift_name and frappe.db.exists("EORL Regime Shift", regime_shift_name):
		shift_doc = frappe.get_doc("EORL Regime Shift", regime_shift_name)
		regime_shift_payload = {
			"name": shift_doc.name,
			"trigger_episode": shift_doc.trigger_episode,
			"parameter_delta_json": frappe.parse_json(shift_doc.parameter_delta_json or "{}"),
		}
	elif run_doc.regime_shift_snapshot_json:
		regime_shift_payload = frappe.parse_json(run_doc.regime_shift_snapshot_json)

	scenario = frappe.parse_json(run_doc.scenario_snapshot_json or "{}")
	case_fn = frappe.get_attr(scenario["scenario_generator"]) if scenario.get("scenario_generator") else generate_case
	outcome_model = scenario.get("outcome_model") or "receipt_keyed_v1"
	return [
		case_fn(seed=run_doc.run_seed, episode=n, regime_shift=regime_shift_payload, outcome_model=outcome_model)
		for n in range(1, episode_count + 1)
	]


def build_model_metadata(run_doc) -> dict:
	agent_snapshots = frappe.parse_json(run_doc.agent_snapshots_json or "{}")
	profile_names = {snap.get("model_profile") for snap in agent_snapshots.values() if snap.get("model_profile")}
	metadata = {}
	for name in profile_names:
		if frappe.db.exists("EORL Model Profile", name):
			doc = frappe.get_doc("EORL Model Profile", name)
			metadata[name] = {
				"provider": doc.provider,
				"model_name": doc.model_name,
				"temperature": doc.temperature,
				"top_p": doc.top_p,
				"max_tokens": doc.max_tokens,
				# api_key_reference deliberately omitted: a reference,
				# never the secret, and not needed to interpret results.
			}
	return metadata


def build_requirements_lock(env_metadata: dict) -> str:
	return (
		f"frappe=={env_metadata['frappe_version']} ({env_metadata['frappe_commit']})\n"
		f"erpnext=={env_metadata['erpnext_version']} ({env_metadata['erpnext_commit']})\n"
		f"eorl_lab=={env_metadata['eorl_lab_commit']}\n"
		f"python=={env_metadata['python_version'].split()[0]}\n"
	)


def build_readme(run_doc, manifest: dict) -> str:
	return f"""# EORL Reproducibility Bundle: {run_doc.name}

Exported from the EORL Lab app (https://github.com/agrimsachdeva/eorl_lab).

## Contents

- `run_manifest.json` -- full configuration snapshot for this run.
- `architecture.json` -- the EORL Architecture document as it was when this run started.
- `resolved_agent_configs/*.json` -- one file per actor slot: its resolved role, model
  profile, memory profile, tool policy, and system instructions, as bound at run start.
- `scenario_stream.jsonl` -- one JSON object per episode: the deterministic case
  (item, quantity, candidate suppliers, latent ground truth) that episode used,
  regenerated from the recorded seed and regime shift, each carrying its own
  `case_hash` for verification.
- `events.jsonl` -- the complete, append-only event log for this run, in order.
- `process_paths.csv` -- one row per episode: its canonical process path (spec
  section 17.1/17.2) and whether the episode succeeded.
- `metrics.csv` -- every computed EORL Metric for this run (spec section 17.3).
- `model_metadata.json` -- resolved model profile parameters for every model
  profile this run's agents used (no API keys).
- `environment_metadata.json` / `code_commit.txt` / `requirements_lock.txt` --
  the exact frappe/erpnext/eorl_lab commits and Python version this run used.

## Recomputing metrics without this Frappe site

Every function in `eorl_lab.analysis` (paths, sequence, coherence, repertoire,
recovery, networks) takes plain dicts shaped exactly like the rows in
`events.jsonl` -- none of them query Frappe. Load `events.jsonl`, group by
episode, and call e.g. `eorl_lab.analysis.paths.process_path(episode_events)`
directly; no live site or model provider access is required.

## Reproducing this run

This run used architecture `{manifest['architecture'].get('name', manifest.get('coordination_mode'))}`,
seed `{manifest['seed']}`, {manifest['episode_count_requested']} episode(s)
{"with regime shift " + manifest['regime_shift']['name'] if manifest.get('regime_shift') and manifest['regime_shift'].get('name') else "with no regime shift"}.

From a site with this same eorl_lab commit ({manifest['environment']['eorl_lab_commit']})
and the same architecture/agent records installed, call:

```python
from eorl_lab.runtime.orchestrator import run_architecture
run_architecture(
    "{manifest['architecture'].get('name', '<architecture name>')}",
    seed={manifest['seed']},
    episode_count={manifest['episode_count_requested']},
    regime_shift={repr(manifest['regime_shift']['name']) if manifest.get('regime_shift') and manifest['regime_shift'].get('name') else None},
)
```

Or, from this site, call `eorl_lab.api.exports.reproduce_run("{run_doc.name}")`,
which does exactly this and verifies the new run's scenario-case hashes and
computed metrics match this bundle's.
"""


def build_full_bundle_zip(run_name: str) -> bytes:
	"""Assembles the spec section 7.9 artifact set as an in-memory zip.
	Calls eorl_lab.api.metrics.compute_run_metrics first if this run has
	no persisted EORL Metric rows yet, so metrics.csv is never empty for
	a completed run."""
	from eorl_lab.api.metrics import compute_run_metrics

	run_doc = frappe.get_doc("EORL Run", run_name)

	if not frappe.db.exists("EORL Metric", {"run": run_name}):
		compute_run_metrics(run_name)

	manifest = build_run_manifest(run_doc)
	scenario_stream = build_scenario_stream(run_doc)
	model_metadata = build_model_metadata(run_doc)
	env_metadata = manifest["environment"]

	episodes = frappe.get_all(
		"EORL Episode",
		filters={"run": run_name},
		fields=["name", "episode_number", "phase", "success"],
		order_by="episode_number asc",
	)
	events = frappe.get_all(
		"EORL Event",
		filters={"run": run_name},
		fields=["*"],
		order_by="sequence_no asc",
	)
	events_by_episode: dict = {}
	for event in events:
		events_by_episode.setdefault(event.episode, []).append(event)

	metrics = frappe.get_all(
		"EORL Metric",
		filters={"run": run_name},
		fields=["metric_name", "episode", "phase", "metric_value", "metric_version"],
	)

	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
		zf.writestr("run_manifest.json", json.dumps(manifest, indent=2, default=str))
		zf.writestr("architecture.json", json.dumps(manifest["architecture"], indent=2, default=str))

		for slot_key, snapshot in manifest["agents"].items():
			zf.writestr(f"resolved_agent_configs/{slot_key}.json", json.dumps(snapshot, indent=2, default=str))

		scenario_lines = "\n".join(json.dumps(case, default=str) for case in scenario_stream)
		zf.writestr("scenario_stream.jsonl", scenario_lines)

		event_lines = "\n".join(json.dumps(dict(e), default=str) for e in events)
		zf.writestr("events.jsonl", event_lines)

		process_paths_csv = io.StringIO()
		writer = csv.writer(process_paths_csv)
		writer.writerow(["episode", "episode_number", "phase", "success", "process_path"])
		for ep in episodes:
			path = process_path(events_by_episode.get(ep.name, []))
			writer.writerow([ep.name, ep.episode_number, ep.phase, ep.success, "|".join(path)])
		zf.writestr("process_paths.csv", process_paths_csv.getvalue())

		metrics_csv = io.StringIO()
		writer = csv.writer(metrics_csv)
		writer.writerow(["metric_name", "episode", "phase", "metric_value", "metric_version"])
		for m in metrics:
			writer.writerow([m.metric_name, m.episode or "", m.phase or "", m.metric_value, m.metric_version])
		zf.writestr("metrics.csv", metrics_csv.getvalue())

		zf.writestr("model_metadata.json", json.dumps(model_metadata, indent=2, default=str))
		zf.writestr("environment_metadata.json", json.dumps(env_metadata, indent=2))
		zf.writestr("code_commit.txt", env_metadata["eorl_lab_commit"] + "\n")
		zf.writestr("requirements_lock.txt", build_requirements_lock(env_metadata))
		zf.writestr("README_REPRODUCE.md", build_readme(run_doc, manifest))

	return buffer.getvalue()
