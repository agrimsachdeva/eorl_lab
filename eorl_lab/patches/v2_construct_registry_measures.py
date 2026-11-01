import frappe

# Submission-day plan section 3.1. Gives five more constructs a real
# measurement function, adds a status to every entry, and registers the
# process constructs that Milestone 7 measured but never listed. Existing
# entries are updated in place; nothing is deleted. Citations are given
# only where the source is certain; the rest say so.
UPDATES = {
	"Centralization": {
		"status": "executable",
		"version": "2.0",
		"source_citations": "Pugh, Hickson, Hinings and Turner (1968), Dimensions of organization structure, Administrative Science Quarterly 13(1).",
		"computational_definition": (
			"Run metric `authority_centralization`. For each authority right held by at least one actor "
			"(decision = has_decision_authority, approval = may_approve, assignment = has_assignment_authority), "
			"the normalized Herfindahl index of its distribution across the architecture's actors "
			"(0 = spread evenly, 1 = held by one actor); the construct value is the mean over held rights. "
			"Read from the run's frozen agent snapshots."
		),
		"measurement_function": "eorl_lab.analysis.constructs.authority_centralization",
		"required_events": "run_initialized (agent snapshots)",
		"validity_notes": (
			"Measures centralization as designed (rights granted), not as exercised. A single-actor "
			"architecture scores 1 by definition. Decision and assignment rights are recorded but not yet "
			"enforced by the authority firewall, so for those two rights the measure describes the formal "
			"structure only. Decision centrality over the handoff network is not included."
		),
	},
	"Specialization": {
		"status": "executable",
		"version": "2.0",
		"source_citations": "Pugh, Hickson, Hinings and Turner (1968), Dimensions of organization structure, Administrative Science Quarterly 13(1).",
		"computational_definition": (
			"Two run metrics. `tool_breadth_specialization` (designed): 1 minus the mean over actors of "
			"|tools held| / |all tools held by anyone|. `task_domain_entropy` (enacted): per actor, Shannon "
			"entropy of the decision domains of the actions it executed, normalized by log2 of the number of "
			"domains in the run, averaged over actors; low values mean actors stay in their own domain."
		),
		"measurement_function": "eorl_lab.analysis.constructs.tool_breadth_specialization",
		"required_events": "tool_result",
		"validity_notes": (
			"Decision domains come from a fixed tool-to-domain table (eorl_lab.analysis.taxonomy, version v1); "
			"a different taxonomy gives different values. finish_turn is excluded from tool breadth."
		),
	},
	"Information asymmetry": {
		"status": "executable",
		"version": "2.0",
		"source_citations": "To be completed by the author.",
		"computational_definition": (
			"Run metric `information_asymmetry` = 1 minus the mean pairwise Jaccard overlap of the actors' "
			"observed state-variable sets. An actor observes the keys of its own tool results and of the handoff "
			"or message payloads it receives."
		),
		"measurement_function": "eorl_lab.analysis.constructs.information_asymmetry",
		"required_events": "tool_result, agent_message_received",
		"validity_notes": (
			"Overlap is over variable names, not values. Every actor still receives the same public case fields, "
			"so asymmetry today comes from what each role's tools return and what is handed to it. Undefined "
			"(null) for single-actor architectures."
		),
	},
	"Routine coherence": {
		"status": "executable",
		"version": "1.1",
		"source_citations": "Feldman and Pentland (2003), Reconceptualizing organizational routines as a source of flexibility and change, Administrative Science Quarterly 48(1).",
	},
	"Adaptive repertoire": {
		"status": "executable",
		"version": "2.0",
		"computational_definition": (
			"Three sets kept apart over the consequential-action view: observed paths, viable paths (criterion v2: "
			"completed, no hard-policy violation, utility >= 0.9) and paths activated after a shock (pre-shock "
			"viable paths used viably post-shock). Run metrics: viable_path_count, viable_path_entropy_v2, "
			"viable_path_concentration, pre_shock_repertoire_size, pre_shock_repertoire_entropy, "
			"post_shock_reuse_rate, post_shock_novel_path_rate, path_extinction_rate_v2, repertoire_retention, "
			"repertoire_activation_latency and adaptive_repertoire_utilization (pre-shock viable paths used "
			"successfully post-shock / pre-shock viable paths)."
		),
		"measurement_function": "eorl_lab.analysis.repertoire.adaptive_repertoire",
		"required_events": "episode_outcome, tool_result",
		"validity_notes": (
			"The Milestone 7 measures (viable_path_entropy and related, criterion v1 = success flag only) remain "
			"available under their original names. With a single repeated scripted policy the pre-shock "
			"repertoire is usually one path, so utilization is 0 or 1; it becomes graded only with exploration "
			"or model-driven actors."
		),
	},
	"Formalization": {"status": "conceptual"},
	"Hierarchy": {"status": "conceptual"},
	"Transactive memory": {"status": "conceptual"},
}

NEW = [
	{
		"construct_name": "Sequential variety",
		"level_of_analysis": "process",
		"status": "executable",
		"version": "1.0",
		"theoretical_definition": "The variety of action sequences through which a work process is enacted across repetitions.",
		"source_citations": "Pentland (2003), Sequential variety in work processes, Organization Science 14(5).",
		"manipulation_strategy": "Vary architecture, actor engine, memory, and the exceptions the scenario produces.",
		"computational_definition": (
			"Run metric `sequence_entropy`: Shannon entropy (bits) over the distribution of distinct episode paths, "
			"under the sequence scope the Analysis Plan registers (all_actions, consequential_actions, "
			"write_actions or actor_function_actions)."
		),
		"measurement_function": "eorl_lab.analysis.sequence.sequence_entropy",
		"required_events": "tool_result",
		"validity_notes": "Treats each whole path as one symbol, so it is sensitive to any optional step; the pilot showed this. Register the scope before launch.",
	},
	{
		"construct_name": "Routine concentration",
		"level_of_analysis": "process",
		"status": "executable",
		"version": "1.0",
		"theoretical_definition": "The degree to which enactments of a routine concentrate on one dominant path.",
		"source_citations": "Feldman and Pentland (2003), Administrative Science Quarterly 48(1).",
		"manipulation_strategy": "Same as Sequential variety.",
		"computational_definition": "Run metric `modal_path_share`: share of episodes that followed the single most common path, under the registered sequence scope.",
		"measurement_function": "eorl_lab.analysis.sequence.modal_path_share",
		"required_events": "tool_result",
		"validity_notes": "Coarse with few episodes per run: with six episodes it moves in steps of 1/6.",
	},
	{
		"construct_name": "Attribute-level path coherence",
		"level_of_analysis": "process",
		"status": "executable",
		"version": "path_coherence_v1",
		"theoretical_definition": "The degree to which consecutive actions in a path share attributes: who acts, in which role and stage, on which object and counterparty, in which exception state, with which kind of tool, in which decision domain.",
		"source_citations": "Kim et al., as cited in the proposal. The formula here is an EORL adaptation; see validity limits.",
		"manipulation_strategy": "Vary architecture (handoffs break actor and role coherence), routine, and exceptions.",
		"computational_definition": (
			"Run metrics `path_coherence_v1` (composite) and `path_coherence_v1_<attribute>` for actor, role, "
			"stage, object_type, counterparty, exception_state, tool_family and decision_domain. For each "
			"attribute, the share of consecutive action pairs within an episode with the same value, pairs with a "
			"missing value skipped, averaged over episodes; the composite is the unweighted mean."
		),
		"measurement_function": "eorl_lab.analysis.attribute_coherence.attribute_coherence",
		"required_events": "tool_result",
		"validity_notes": (
			"The pairwise-agreement formula, within-episode averaging and equal weights are EORL choices. They have "
			"not been checked against the cited paper's own estimator; treat any difference in weighting, "
			"distance or normalization as an adaptation. Counterparty and exception state need event payloads, "
			"so they are missing for exports without payloads."
		),
	},
	{
		"construct_name": "Communication centralization",
		"level_of_analysis": "group",
		"status": "executable",
		"version": "1.0",
		"theoretical_definition": "The degree to which communication flows through one actor.",
		"source_citations": "Freeman (1978/79), Centrality in social networks: conceptual clarification, Social Networks 1(3).",
		"manipulation_strategy": "Vary the EORL Communication Policy graph and the handoff structure.",
		"computational_definition": "Run metric `communication_centralization`: Freeman degree centralization of the undirected, unweighted message graph.",
		"measurement_function": "eorl_lab.analysis.constructs.communication_centralization",
		"required_events": "agent_message_sent",
		"validity_notes": "Undefined with fewer than three communicating actors. With the four-actor specialist chain the value is fixed by the handoff structure unless agents message outside it.",
	},
]


def execute():
	for name, fields in UPDATES.items():
		if frappe.db.exists("EORL Construct", name):
			doc = frappe.get_doc("EORL Construct", name)
			doc.update(fields)
			doc.save(ignore_permissions=True)
	for construct in NEW:
		if not frappe.db.exists("EORL Construct", construct["construct_name"]):
			frappe.get_doc({"doctype": "EORL Construct", **construct}).insert(ignore_permissions=True)
	frappe.db.commit()
