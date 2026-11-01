"""Reviewer-facing endpoints (submission-day plan sections 13, 15, 7).

Everything here is read-only. The walkthrough resolves the records it
points at from EORL Settings.reviewer_walkthrough_json, filling any key
that is missing with the most recent matching record, and reports a
step as unavailable rather than linking to something that does not
exist.
"""
import json
import os

import frappe

READ_ROLES = ["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"]

# Fields that legitimately differ between two runs of a matched
# comparison and are ignored by compare_run_configurations.
_IDENTITY_FIELDS = {
	"name", "template", "architecture_name", "creation", "modified", "modified_by", "owner", "idx", "docstatus",
	"parent", "parentfield", "parenttype", "agent_template", "description",
}


def _settings_pointers() -> dict:
	raw = frappe.db.get_single_value("EORL Settings", "reviewer_walkthrough_json")
	try:
		return json.loads(raw) if raw else {}
	except ValueError:
		return {}


def _exists(doctype, name):
	return bool(name) and frappe.db.exists(doctype, name)


def _latest(doctype, filters=None, order_by="creation desc"):
	rows = frappe.get_all(doctype, filters=filters or {}, pluck="name", order_by=order_by, limit_page_length=1)
	return rows[0] if rows else None


def _resolve_pointers() -> dict:
	p = _settings_pointers()
	out = {}
	out["architecture"] = p.get("architecture") if _exists("EORL Architecture", p.get("architecture")) else _latest(
		"EORL Architecture", {"coordination_mode": "specialist_handoff"})
	out["llm_run"] = p.get("llm_run") if _exists("EORL Run", p.get("llm_run")) else (
		_latest("EORL Run", {"actor_engine": "llm", "status": "completed"}) or _latest("EORL Run", {"status": "completed"}))
	episode = p.get("episode")
	if not _exists("EORL Episode", episode) and out["llm_run"]:
		episode = _latest("EORL Episode", {"run": out["llm_run"]}, order_by="episode_number asc")
	out["episode"] = episode
	out["process_run"] = p.get("process_run") if _exists("EORL Run", p.get("process_run")) else out["llm_run"]
	parent = p.get("branch_parent")
	if not _exists("EORL Run", parent):
		parent = frappe.db.get_value("EORL Branch", {}, "parent_run", order_by="creation desc")
	out["branch_parent"] = parent
	out["branch_children"] = frappe.get_all("EORL Branch", filters={"parent_run": parent}, pluck="child_run") if parent else []
	out["analysis_plan"] = p.get("analysis_plan") if _exists("EORL Analysis Plan", p.get("analysis_plan")) else _latest("EORL Analysis Plan")
	result = p.get("analysis_result")
	if not _exists("EORL Analysis Result", result) and out["analysis_plan"]:
		result = _latest("EORL Analysis Result", {"analysis_plan": out["analysis_plan"], "is_primary_test": 1}) or _latest(
			"EORL Analysis Result", {"analysis_plan": out["analysis_plan"]})
	out["analysis_result"] = result
	out["export_run"] = p.get("export_run") if _exists("EORL Run", p.get("export_run")) else out["llm_run"]
	out["adaptation_run"] = p.get("adaptation_run") if _exists("EORL Run", p.get("adaptation_run")) else _latest(
		"EORL Run", {"regime_shift_snapshot_json": ["is", "set"], "status": "completed"})
	out["second_routine_run"] = p.get("second_routine_run") if _exists("EORL Run", p.get("second_routine_run")) else _latest(
		"EORL Run", {"routine_template": "Order-to-Cash", "status": "completed"})
	return out


@frappe.whitelist()
def get_reviewer_walkthrough() -> dict:
	frappe.only_for(READ_ROLES)
	r = _resolve_pointers()

	def step(n, title, what, look_for, route=None, route_options=None, record=None, extra=None):
		return {"n": n, "title": title, "what": what, "look_for": look_for, "route": route,
			"route_options": route_options, "record": record, "available": bool(route), **(extra or {})}

	slug = frappe.scrub
	steps = [
		step(1, "Inspect an organizational architecture",
			"An architecture is configuration, not code: actor slots, each bound to an Agent Template with its own tool policy, memory and model profile.",
			"The actor slots table, the communication policy and the routine template.",
			f"/app/eorl-architecture/{r['architecture']}" if r["architecture"] else None, record=r["architecture"]),
		step(2, "Inspect one run",
			"A run is one independent history: a seed, a frozen snapshot of the architecture and agents, and a sequence of episodes.",
			"Snapshots, actor engine, routine template, code commit, telemetry and failure type.",
			f"/app/eorl-run/{r['llm_run']}" if r["llm_run"] else None, record=r["llm_run"]),
		step(3, "Inspect one episode",
			"Every model request, authority decision, tool call, ERP mutation and message is an append-only event with a payload hash.",
			"tool_authorized / tool_denied events (the authority check runs outside the model) and erp_mutation events naming real ERPNext documents.",
			"/app/eorl-trace-explorer" if r["episode"] else None, {"run": r["llm_run"], "episode": r["episode"]}, r["episode"]),
		step(4, "Inspect the process",
			"The directly-follows graph, variants and swimlane, under any registered sequence view.",
			"Switch the scope between all_actions and consequential_actions: the same events, two registered views. Actor continuity, functional continuity and attribute-level coherence are shown separately.",
			"/app/eorl-process-explorer" if r["process_run"] else None, {"run": r["process_run"]}, r["process_run"]),
		step(5, "Inspect a matched branch",
			"A branch clones actor memory at an episode and continues the same exogenous stream under a different intervention.",
			"Parent and children share history through the branch point and diverge after it.",
			"/app/eorl-paired-branch-inference" if r["branch_parent"] else None, {"parent_run": r["branch_parent"]}, r["branch_parent"],
			{"children": r["branch_children"]}),
		step(6, "Inspect an Analysis Plan",
			"The plan fixes the outcome, unit of analysis, sequence scope, tests, equivalence bounds, multiplicity family and interpretation rule before results exist.",
			"analysis_unit = run (the independence guardrail), sequence_scope, and the structured interpretation rules.",
			f"/app/eorl-analysis-plan/{r['analysis_plan']}" if r["analysis_plan"] else None, record=r["analysis_plan"]),
		step(7, "Inspect the result",
			"Each result names the run IDs, counts, metric version and package version that produced it.",
			"Raw and adjusted p, Hedges' g with its bootstrap interval, and the registered interpretation label.",
			f"/app/eorl-analysis-result/{r['analysis_result']}" if r["analysis_result"] else None, record=r["analysis_result"]),
		step(8, "Inspect reproducibility",
			"A run exports as a bundle: manifest, scenario stream, events, metrics and environment versions.",
			"The manifest's code commit and scenario case hashes.",
			"/app/eorl-reproducibility" if r["export_run"] else None, {"run": r["export_run"]}, r["export_run"]),
		step(9, "Inspect the Construct Registry",
			"Constructs are defined once and reused across studies, each with a manipulation, a measurement function and its known limits.",
			"The status column: which constructs are executable on recorded runs and which are only defined.",
			"/app/eorl-construct"),
		step(10, "Inspect adaptation to a path-invalidating shock",
			"A supplier-quality reversal makes the previously dominant choice the worse one.",
			"Supplier choice before and after the shock, utility, and the observed / viable / activated repertoire sets.",
			"/app/eorl-adaptation-view" if r["adaptation_run"] else None, {"run": r["adaptation_run"]}, r["adaptation_run"]),
		step(11, "Inspect a second routine",
			"Order-to-cash runs through the same orchestrator, event store and Process Explorer as procure-to-pay.",
			"A different routine template, roles and ERP documents, with no change to the orchestrator.",
			"/app/eorl-process-explorer" if r["second_routine_run"] else None, {"run": r["second_routine_run"]}, r["second_routine_run"]),
	]
	return {"steps": steps, "artifact": _artifact_manifest_summary(), "user_is_read_only": not frappe.has_permission("EORL Run", "create")}


def _artifact_manifest_path() -> str:
	return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "artifact_manifest.json")


def _artifact_manifest_summary() -> dict:
	try:
		with open(_artifact_manifest_path()) as fh:
			manifest = json.load(fh)
	except (OSError, ValueError):
		return {}
	return {k: manifest.get(k) for k in ("name", "version", "commit", "release_tag", "submission_date", "tests")}


@frappe.whitelist()
def get_artifact_manifest() -> dict:
	frappe.only_for(READ_ROLES)
	try:
		with open(_artifact_manifest_path()) as fh:
			return json.load(fh)
	except (OSError, ValueError):
		frappe.throw("artifact_manifest.json is missing; run scripts/generate_artifact_manifest.py.")


# ---------------------------------------------------------------------------
# Special-issue evaluation matrix (plan section 15)
# ---------------------------------------------------------------------------

EVALUATION_MATRIX = [
	{
		"criterion": "Novelty",
		"capability": "Organizational theories instantiated as executable structures (roles, authority, memory, communication, routines) acted on by semantically capable computational actors, with counterfactual histories of the same organization.",
		"evidence": "Architecture, Agent Template, Tool Policy and Routine Template documents; counterfactual branching (EORL Branch); actor engine chosen independently of architecture.",
		"verify": "Reviewer Start Here steps 1, 5 and 11.",
		"limitation": "One semantic model family (Qwen3 27B) has been used for model-driven runs.",
	},
	{
		"criterion": "Feasibility",
		"capability": "A working Frappe/ERPNext application with an automated test suite, scripted validation runs and a pre-registered language-model pilot.",
		"evidence": "{test_count} automated tests; {run_count} recorded runs on this site, {llm_run_count} with a language-model engine.",
		"verify": "Run list filtered by actor engine; the test count in artifact_manifest.json.",
		"limitation": "The language-model pilot is 16 runs of one routine and one scenario.",
	},
	{
		"criterion": "Auditability",
		"capability": "Append-only event store with payload hashes; authority decisions logged outside the model; every analysis result names the runs, metric version and package version behind it.",
		"evidence": "{event_count} events; EORL Event rejects edits and deletes; EORL Analysis Result provenance fields.",
		"verify": "Reviewer Start Here steps 3 and 7.",
		"limitation": "Event immutability is enforced by the application, not by the database.",
	},
	{
		"criterion": "Ethicality",
		"capability": "No human participants; synthetic company and suppliers; an authority firewall that the model cannot override; a self-hosted model so no case data leaves the lab.",
		"evidence": "Demonstration site holds synthetic data only; authority.evaluate runs on every tool call; the API key is held in site configuration, never in a record.",
		"verify": "Trace Explorer: tool_denied events and their reason codes.",
		"limitation": "Synthetic data cannot show how the findings transfer to human organizations.",
	},
	{
		"criterion": "Reproducibility",
		"capability": "Frozen run snapshots, seeded scenarios with case hashes, a matched exogenous outcome model, export bundles, scripted reproduction, seeded statistics.",
		"evidence": "Run manifests with code commit and scenario hashes; reproduce_run; random_seed on every Analysis Plan.",
		"verify": "Reviewer Start Here step 8; reproduce a scripted run from the Reproducibility page (researcher role).",
		"limitation": "Model-driven runs are not bit-for-bit reproducible; only their configuration, scenario stream and trace are.",
	},
	{
		"criterion": "Scalability",
		"capability": "Runs are independent units; queued background execution; per-run model-call, token and wallclock telemetry for planning.",
		"evidence": "eorl_lab.api.queue; EORL Run telemetry fields; pilot cost: about 9 minutes per six-episode run.",
		"verify": "EORL Run list: model_calls, total_tokens and wallclock_seconds columns.",
		"limitation": "One bench and one shared ERP company; branches are not isolated at the ERP layer; no distributed workers.",
	},
	{
		"criterion": "Potential adoption",
		"capability": "Open-source stack (Frappe, ERPNext); configuration through ordinary forms; pluggable routines, actor engines, memory backends and model providers.",
		"evidence": "{routine_count} routine templates; {construct_count} constructs, {executable_construct_count} executable; OpenAI-compatible provider.",
		"verify": "Routine Template and Construct lists.",
		"limitation": "Researchers still compose agents and architectures in plain forms; there is no graphical designer.",
	},
	{
		"criterion": "Frontier expansion",
		"capability": "Theory to executable organization to counterfactual history to process evidence to design-aware inference, in one instrument.",
		"evidence": "Theory Compiler; Analysis Plans with an independence guardrail, paired-branch checks, TOST, multiplicity correction, effect-size intervals and registered interpretation rules.",
		"verify": "Reviewer Start Here steps 4 to 7.",
		"limitation": "The first theory demonstration is illustrative; its propositions are not yet tested at the registered sample size.",
	},
]


@frappe.whitelist()
def get_evaluation_matrix() -> dict:
	frappe.only_for(READ_ROLES)
	tests = (_artifact_manifest_summary().get("tests") or {}).get("count")
	counts = {
		"test_count": tests if tests is not None else "see artifact_manifest.json",
		"run_count": frappe.db.count("EORL Run"),
		"llm_run_count": frappe.db.count("EORL Run", {"actor_engine": "llm"}),
		"event_count": frappe.db.count("EORL Event"),
		"routine_count": frappe.db.count("EORL Routine Template"),
		"construct_count": frappe.db.count("EORL Construct"),
		"executable_construct_count": frappe.db.count("EORL Construct", {"status": "executable"}),
	}
	rows = [{k: (v.format(**counts) if isinstance(v, str) else v) for k, v in row.items()} for row in EVALUATION_MATRIX]
	return {"rows": rows, "counts": counts}


# ---------------------------------------------------------------------------
# Condition manifests (plan section 7)
# ---------------------------------------------------------------------------

def _flatten(value, prefix=""):
	if isinstance(value, dict):
		out = {}
		for k, v in value.items():
			if k in _IDENTITY_FIELDS:
				continue
			out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
		return out
	if isinstance(value, list):
		if all(isinstance(v, dict) for v in value):
			out = {}
			for i, v in enumerate(value):
				out.update(_flatten(v, f"{prefix}[{i}]"))
			return out
		return {prefix: value}
	return {prefix: value}


def configuration_difference(run_a: str, run_b: str) -> dict:
	"""Field-by-field difference between two runs' frozen configurations
	(architecture snapshot, agent snapshots with resolved profile and
	policy contents, actor engine, routine, regime). Names of the
	documents themselves are ignored, so two conditions built from
	different documents with the same contents show no difference."""
	def config(run_name):
		run = frappe.get_doc("EORL Run", run_name)
		architecture = frappe.parse_json(run.architecture_snapshot_json or "{}")
		agents = frappe.parse_json(run.agent_snapshots_json or "{}")
		for snap in agents.values():
			for key in ("model_profile", "memory_profile", "tool_policy"):
				snap.pop(key, None)  # compared through their resolved *_config contents
		return _flatten({
			"architecture": {k: architecture.get(k) for k in ("coordination_mode", "communication_policy", "process_grammar",
				"routine_template", "stage_gated_tools")},
			"agents": {snap.get("organizational_role") or slot: snap for slot, snap in agents.items()},
			"actor_engine": run.get("actor_engine"),
			"routine_template": run.get("routine_template"),
			"regime_shift": frappe.parse_json(run.regime_shift_snapshot_json or "null"),
			"outcome_model": frappe.parse_json(run.scenario_snapshot_json or "{}").get("outcome_model"),
		})

	a, b = config(run_a), config(run_b)
	differing = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
	return {"run_a": run_a, "run_b": run_b, "differing_fields": differing,
		"values": {k: {"a": a.get(k), "b": b.get(k)} for k in differing}}


@frappe.whitelist()
def compare_run_configurations(run_a: str, run_b: str, allowed_prefixes=None) -> dict:
	"""Confirms which configuration fields differ between two runs. With
	`allowed_prefixes` (for example ["agents.General Purchasing
	Agent.memory_profile_config"]) it also reports whether every
	difference falls under them, i.e. whether only the manipulated
	factor differs."""
	frappe.only_for(READ_ROLES)
	if isinstance(allowed_prefixes, str):
		allowed_prefixes = frappe.parse_json(allowed_prefixes)
	result = configuration_difference(run_a, run_b)
	if allowed_prefixes:
		outside = [f for f in result["differing_fields"] if not any(f.startswith(p) for p in allowed_prefixes)]
		result["only_allowed_fields_differ"] = not outside
		result["unexpected_differences"] = outside
	return result
