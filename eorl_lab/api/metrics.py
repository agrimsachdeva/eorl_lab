import frappe
from frappe.utils import now_datetime

from eorl_lab.analysis import (
	adaptation, attribute_coherence, coherence, constructs, networks, paths, recovery, repertoire, sequence, taxonomy,
)

METRIC_VERSION = "v1"

# Since the submission-day build the recovery metrics are computed on
# episode utility (eorl_lab.analysis.repertoire.episode_utility) rather
# than the 0/1 success flag, so a shock that lowers quality without
# causing a failure is visible. Only these change definition, so only
# these carry the new version.
RECOVERY_METRIC_VERSION = "v2+utility"
_RECOVERY_METRICS = {
	"immediate_post_shock_drop", "episodes_to_recover_90pct", "area_under_recovery_curve", "post_shock_error_rate",
}

SCOPED_SEQUENCE_METRICS = ("unique_sequence_count", "sequence_entropy", "modal_path_share", "transition_entropy")

_REPERTOIRE_DEPENDENT_METRICS = {
	"viable_unique_path_count", "viable_path_entropy", "concentration_top1",
	"proportion_repertoire_reused_after_shock", "novel_viable_paths_after_shock",
	"path_extinction_rate", "change_in_path_concentration_top1",
}


_REPERTOIRE_V2_METRICS = {
	"observed_path_count", "viable_path_count", "viable_path_entropy_v2", "viable_path_concentration",
	"pre_shock_repertoire_size", "pre_shock_repertoire_entropy", "post_shock_reuse_rate", "post_shock_novel_path_rate",
	"path_extinction_rate_v2", "repertoire_retention", "repertoire_activation_latency", "adaptive_repertoire_utilization",
	"activated_after_shock_paths",
}
_CONSTRUCT_METRICS = {
	"information_asymmetry", "authority_centralization", "tool_breadth_specialization",
	"task_domain_entropy", "communication_centralization",
}


def metric_version(metric_name: str) -> str:
	"""The definition version a persisted metric (or an analysis result
	computed from it) carries."""
	return _metric_version(metric_name)


def _metric_version(metric_name: str) -> str:
	base = metric_name.split("@", 1)[0]
	scope = metric_name.split("@", 1)[1] if "@" in metric_name else None
	if base.startswith("path_coherence_v1"):
		version = attribute_coherence.PATH_COHERENCE_VERSION
	elif base in _REPERTOIRE_V2_METRICS:
		version = f"v2+viability:{repertoire.VIABILITY_CRITERION_V2}"
	elif base in _REPERTOIRE_DEPENDENT_METRICS:
		version = f"{METRIC_VERSION}+viability:{repertoire.VIABILITY_CRITERION_VERSION}"
	elif base in _CONSTRUCT_METRICS:
		version = f"constructs:{constructs.CONSTRUCT_MEASURES_VERSION}"
	elif base in _RECOVERY_METRICS:
		version = RECOVERY_METRIC_VERSION
	else:
		version = METRIC_VERSION
	if scope:
		version += f"+scope:{scope}+taxonomy:{taxonomy.TAXONOMY_VERSION}"
	return version


def _episode_data(run_name: str):
	"""Fetch per-episode events/outcomes/phases for a run as plain
	dicts/lists -- the same shape the pure eorl_lab.analysis functions
	expect. This is the only place in the metrics pipeline that touches
	Frappe; everything downstream works equally well on an exported
	JSONL bundle outside Frappe (spec section 17's closing requirement)."""
	episodes = frappe.get_all(
		"EORL Episode",
		filters={"run": run_name},
		fields=["name", "episode_number", "phase", "outcome_json"],
		order_by="episode_number asc",
	)
	all_events = frappe.get_all(
		"EORL Event",
		filters={"run": run_name},
		fields=[
			"episode", "event_type", "run", "actor_slot", "actor_instance_id",
			"target_id", "success", "wallclock_timestamp", "payload_json",
		],
		order_by="sequence_no asc",
	)
	events_by_episode: dict = {}
	for event in all_events:
		events_by_episode.setdefault(event.episode, []).append(event)

	episode_paths, episode_events, outcomes, phases = [], [], [], []
	for ep in episodes:
		events_for_episode = events_by_episode.get(ep.name, [])
		episode_events.append(events_for_episode)
		episode_paths.append(paths.process_path(events_for_episode))
		outcomes.append(frappe.parse_json(ep.outcome_json or "{}"))
		phases.append(ep.phase)

	return episode_events, episode_paths, outcomes, phases


def _save_metric(run_name, metric_name, value, episode=None, phase=None):
	numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
	frappe.get_doc(
		{
			"doctype": "EORL Metric",
			"run": run_name,
			"episode": episode,
			"phase": phase,
			"metric_name": metric_name,
			"metric_value": value if numeric else None,
			# Float columns cannot hold NULL in Frappe, so an undefined value
			# is stored as 0 and flagged here.
			"value_undefined": 1 if value is None else 0,
			"metric_version": _metric_version(metric_name),
			"computed_at": now_datetime(),
			"metric_json": None if numeric or value is None else frappe.as_json(value),
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def compute_run_metrics(run_name: str) -> dict:
	"""Computes and persists the Milestone 7 metric set for one run
	(spec section 17.3), via the pure functions in eorl_lab.analysis --
	the same functions anyone could call directly on an exported bundle
	outside Frappe. Milestone 7 deviation: ground-truth-driven
	performance measures (decision accuracy, financial cost) aren't
	computed, because the scenario generator doesn't yet produce
	ground-truth-driven probabilistic outcomes (spec section 11) --
	"performance" here is episode success (1.0/0.0), which is honest but
	currently non-discriminating on demo data where almost everything
	succeeds."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])

	episode_events, episode_paths, outcomes, phases = _episode_data(run_name)
	# Recovery metrics use utility (RECOVERY_METRIC_VERSION); success_rate
	# stays the share of episodes that completed.
	performance = [repertoire.episode_utility(o) for o in outcomes]
	successes = [1.0 if o.get("success") else 0.0 for o in outcomes]
	all_events_flat = [e for group in episode_events for e in group]
	has_shock = any(ph in ("shock", "recovery") for ph in phases)

	computed = {}
	# Submission-day plan section 14: a read-only reviewer can compute
	# metrics but never writes them.
	persist = bool(frappe.has_permission("EORL Metric", "create"))

	def record(name, value):
		computed[name] = value
		if persist:
			_save_metric(run_name, name, value)

	# Outcome (SOTA Milestone 5: a named, persisted run-level metric --
	# previously only computed ad hoc inline by compare_runs below, not
	# available for eorl_lab.api.analysis.compare_groups to read as an
	# EORL Analysis Plan.outcome_metric).
	record("success_rate", (sum(successes) / len(successes)) if successes else None)

	# Routine structure
	record("unique_sequence_count", sequence.unique_sequence_count(episode_paths))
	record("sequence_entropy", sequence.sequence_entropy(episode_paths))
	record("modal_path_share", sequence.modal_path_share(episode_paths))
	record("transition_entropy", sequence.transition_entropy(episode_paths))
	record("directly_follows_graph", sequence.directly_follows_graph(episode_paths))

	# Path coherence
	record("actor_switch_rate", coherence.actor_switch_rate(all_events_flat))
	record("actor_continuity", coherence.actor_continuity(all_events_flat))
	record("average_actor_run_length", coherence.average_actor_run_length(all_events_flat))
	record("functional_switch_rate", coherence.functional_switch_rate(all_events_flat))
	record("functional_continuity", coherence.functional_continuity(all_events_flat))
	record("stage_continuity", coherence.stage_continuity(all_events_flat))
	record("repeated_path_probability", coherence.repeated_path_probability(episode_paths))

	# Adaptive repertoire
	record("viable_unique_path_count", len(repertoire.viable_unique_paths(episode_paths, outcomes)))
	record("viable_path_entropy", repertoire.viable_path_entropy(episode_paths, outcomes))
	record("concentration_top1", repertoire.concentration_in_top_k(episode_paths, outcomes, k=1))

	if any(ph in ("shock", "recovery") for ph in phases):
		record(
			"proportion_repertoire_reused_after_shock",
			repertoire.proportion_repertoire_reused_after_shock(episode_paths, outcomes, phases),
		)
		record("novel_viable_paths_after_shock", repertoire.novel_viable_paths_after_shock(episode_paths, outcomes, phases))
		record("path_extinction_rate", repertoire.path_extinction_rate(episode_paths, outcomes, phases))

		# Adaptation
		record("immediate_post_shock_drop", recovery.immediate_post_shock_drop(performance, phases))
		record("episodes_to_recover_90pct", recovery.episodes_to_recover(performance, phases, 0.9))
		record("area_under_recovery_curve", recovery.area_under_recovery_curve(performance, phases))
		record("post_shock_error_rate", recovery.post_shock_error_rate(performance, phases))
		record("change_in_sequence_entropy", recovery.change_in_sequence_entropy(episode_paths, phases))
		record(
			"change_in_path_concentration_top1",
			recovery.change_in_path_concentration(episode_paths, outcomes, phases, k=1),
		)

	# Communication network
	network = networks.communication_network(all_events_flat)
	record("communication_network", network)

	# --- Submission-day additions -------------------------------------
	record("mean_utility", (sum(performance) / len(performance)) if performance else None)

	# Registered sequence views (plan section 19): the same run, other scopes.
	scoped_paths = {}
	for scope in taxonomy.SEQUENCE_SCOPES[1:]:
		scoped_paths[scope] = [paths.process_path(ev, scope=scope) for ev in episode_events]
		record(taxonomy.scope_metric_name("unique_sequence_count", scope), sequence.unique_sequence_count(scoped_paths[scope]))
		record(taxonomy.scope_metric_name("sequence_entropy", scope), sequence.sequence_entropy(scoped_paths[scope]))
		record(taxonomy.scope_metric_name("modal_path_share", scope), sequence.modal_path_share(scoped_paths[scope]))
		record(taxonomy.scope_metric_name("transition_entropy", scope), sequence.transition_entropy(scoped_paths[scope]))

	# Attribute-level path coherence (plan section 4).
	for scope in ("all_actions", "consequential_actions"):
		by_attribute = attribute_coherence.attribute_coherence(all_events_flat, scope=scope)
		record(taxonomy.scope_metric_name("path_coherence_v1", scope), by_attribute["composite"])
		record(taxonomy.scope_metric_name("path_coherence_v1_by_attribute", scope), by_attribute)
		for attribute in attribute_coherence.ATTRIBUTES:
			record(taxonomy.scope_metric_name(f"path_coherence_v1_{attribute}", scope), by_attribute[attribute])

	# Adaptive repertoire v2 on the consequential view (plan section 6).
	for name, value in repertoire.adaptive_repertoire(scoped_paths["consequential_actions"], outcomes, phases).items():
		if name in ("viability_criterion", "utility_threshold"):
			continue
		record("viable_path_entropy_v2" if name == "viable_path_entropy" else name, value)

	# Shock adaptation (plan section 5).
	if has_shock:
		chosen = [_chosen_counterparty(ev) for ev in episode_events]
		for name, value in adaptation.shock_adaptation(scoped_paths["consequential_actions"], outcomes, phases, chosen).items():
			record(name, value)

	# Construct measures (plan section 3.1).
	grants, actor_tools = _authority_configuration(run_name)
	asymmetry = constructs.information_asymmetry(all_events_flat)
	record("information_asymmetry", asymmetry["asymmetry"] if asymmetry else None)
	centralization = constructs.authority_centralization(grants)
	record("authority_centralization", centralization["centralization"] if centralization else None)
	breadth = constructs.tool_breadth_specialization(actor_tools)
	record("tool_breadth_specialization", breadth["specialization"] if breadth else None)
	domain_entropy = constructs.task_domain_entropy(all_events_flat)
	record("task_domain_entropy", domain_entropy["mean_normalized_entropy"] if domain_entropy else None)
	record("communication_centralization", constructs.communication_centralization(network))

	return {"run": run_name, "metrics": computed}


def _chosen_counterparty(events_for_episode: list):
	for event in paths.extract_canonical_events(events_for_episode):
		if event.decision_value:
			return event.decision_value
	return None


def _authority_configuration(run_name: str):
	"""({actor: {right: bool}}, {actor: [tools]}) from the run's own agent
	snapshot. Runs recorded before snapshots carried the policy contents
	fall back to the current EORL Tool Policy document."""
	snapshots = frappe.parse_json(frappe.db.get_value("EORL Run", run_name, "agent_snapshots_json") or "{}")
	grants, actor_tools = {}, {}
	for slot, snap in snapshots.items():
		config = snap.get("tool_policy_config")
		if not config and snap.get("tool_policy") and frappe.db.exists("EORL Tool Policy", snap["tool_policy"]):
			policy = frappe.get_doc("EORL Tool Policy", snap["tool_policy"])
			config = {"tools": [r.tool_name for r in policy.allowed_semantic_tools], "may_approve": policy.may_approve,
				"has_decision_authority": policy.has_decision_authority, "has_assignment_authority": policy.has_assignment_authority}
		if not config:
			continue
		actor = snap.get("organizational_role") or slot
		grants[actor] = {"decision": bool(config.get("has_decision_authority")), "approval": bool(config.get("may_approve")),
			"assignment": bool(config.get("has_assignment_authority"))}
		actor_tools[actor] = config.get("tools") or []
	return grants, actor_tools


@frappe.whitelist()
def compare_runs(runs) -> list:
	"""Backs the Compare Runs page (spec section 7.8). Milestone 6's raw
	aggregates, now enriched with Milestone 7's real coherence/variety
	metrics (computed inline, not persisted -- compute_run_metrics is
	the entrypoint that persists EORL Metric rows)."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher", "EORL Viewer"])
	if isinstance(runs, str):
		runs = frappe.parse_json(runs)

	comparison = []
	for run_name in runs:
		run_doc = frappe.get_doc("EORL Run", run_name)
		episode_events, episode_paths, outcomes, _phases = _episode_data(run_name)
		all_events_flat = [e for group in episode_events for e in group]
		distinct_actors = {e.actor_slot for group in episode_events for e in group if e.actor_slot}

		comparison.append(
			{
				"run": run_name,
				"status": run_doc.status,
				"run_seed": run_doc.run_seed,
				"episode_count": len(episode_events),
				"success_rate": (sum(1 for o in outcomes if o.get("success")) / len(outcomes)) if outcomes else None,
				"distinct_actor_count": len(distinct_actors),
				"actor_slots": sorted(distinct_actors),
				"event_count": run_doc.event_count,
				"unique_sequence_count": sequence.unique_sequence_count(episode_paths),
				"sequence_entropy": sequence.sequence_entropy(episode_paths),
				"actor_continuity": coherence.actor_continuity(all_events_flat),
				"average_actor_run_length": coherence.average_actor_run_length(all_events_flat),
			}
		)
	return comparison
