import frappe

# SOTA Milestone 4 (V2 section 20): the 8 "initial constructs" the spec
# names explicitly. Only two (Routine coherence, Adaptive repertoire)
# have a real measurement_function today -- the rest are seeded with
# measurement_function left BLANK and an honest validity_notes
# explaining what's missing, rather than pointing at something that
# doesn't exist. The registry's value is in being a truthful map of
# theory-to-implementation as it stands today, not an aspirational one.
CONSTRUCTS = [
	{
		"construct_name": "Centralization",
		"level_of_analysis": "organization",
		"theoretical_definition": "The degree to which decision, assignment, and approval rights are concentrated in few actors rather than distributed broadly.",
		"manipulation_strategy": "Vary the concentration of has_decision_authority / has_assignment_authority / may_approve grants across an architecture's EORL Tool Policy documents.",
		"computational_definition": "An HHI-style concentration index over which actors hold decision/assignment/approval authority, plus a decision-centrality measure over the communication/handoff network.",
		"measurement_function": "",
		"required_events": "task_assigned, tool_authorized",
		"validity_notes": (
			"Not yet implemented: no authority-concentration (HHI) or decision-centrality "
			"metric exists in eorl_lab.analysis. EORL Tool Policy's has_decision_authority / "
			"has_assignment_authority (SOTA Milestone 1) record the raw per-actor grants this "
			"would be computed FROM; nothing aggregates them into an index yet."
		),
	},
	{
		"construct_name": "Specialization",
		"level_of_analysis": "actor",
		"theoretical_definition": "The breadth of task and tool domains a given actor is authorized to act in.",
		"manipulation_strategy": "Vary the breadth of EORL Tool Policy.allowed_semantic_tools per actor slot.",
		"computational_definition": "Actor task entropy over the distribution of distinct tool/task domains an actor is authorized for, and raw tool-breadth count.",
		"measurement_function": "",
		"required_events": "tool_authorized",
		"validity_notes": (
			"Not yet implemented as a metric function. EORL Tool Policy.allowed_semantic_tools "
			"is the raw manipulation surface (tool breadth = len(allowed_semantic_tools)); no "
			"function in eorl_lab.analysis aggregates this into an entropy measure yet."
		),
	},
	{
		"construct_name": "Formalization",
		"level_of_analysis": "organization",
		"theoretical_definition": "The number and strength of hard and soft process rules governing action.",
		"manipulation_strategy": "Vary the number of EORL Process Grammar transitions marked mandatory/prohibited, and EORL Tool Policy's soft_rule_large_qty_threshold (SOTA Milestone 1).",
		"computational_definition": "A count/strength index over hard constraints (authority.evaluate() hard blocks) and soft rules (soft_violations) actually exercised in a run's trace.",
		"measurement_function": "",
		"required_events": "tool_denied, soft_rule_violation",
		"validity_notes": (
			"Not yet implemented as a metric function. EORL Process Grammar (SOTA Milestone 1) "
			"and EORL Tool Policy's soft-rule fields are the real manipulation surface; no "
			"function aggregates observed tool_denied/soft_rule_violation events into a "
			"formalization index yet."
		),
	},
	{
		"construct_name": "Information asymmetry",
		"level_of_analysis": "dyad",
		"theoretical_definition": "The degree of non-overlap between two actors' observation sets.",
		"manipulation_strategy": "Vary which case/scratch fields each actor's EORL Tool Policy exposes via its sensing tools.",
		"computational_definition": "Set-overlap (e.g. Jaccard) between two actors' memory_retrieval/environment_observed payloads over a run.",
		"measurement_function": "",
		"required_events": "environment_observed, memory_retrieval",
		"validity_notes": (
			"Not yet implemented: no observation-set-overlap metric exists. Every actor today "
			"observes the full case's public fields (SOTA Milestone 3's _public_case), so there "
			"is currently no real asymmetry condition built to measure in the first place."
		),
	},
	{
		"construct_name": "Hierarchy",
		"level_of_analysis": "organization",
		"theoretical_definition": "The depth of approval/assignment chains an action must pass through.",
		"manipulation_strategy": "Vary the number of approval stages in an EORL Process Grammar / specialist_handoff actor_slots sequence.",
		"computational_definition": "Depth of the approval/assignment chain actually traversed per episode, from EORL Task Assignment and task_assigned/tool_authorized(may_approve) events.",
		"measurement_function": "",
		"required_events": "task_assigned, tool_authorized",
		"validity_notes": "Not yet implemented as a metric function; EORL Task Assignment (SOTA Milestone 1) records the raw assignment data a depth measure would walk.",
	},
	{
		"construct_name": "Transactive memory",
		"level_of_analysis": "group",
		"theoretical_definition": "The accuracy and sharedness of actors' beliefs about where expertise is located, and the system's ability to successfully route to it.",
		"manipulation_strategy": "Enable shared/transactive memory (EORL Memory Profile.local_backend = 'shared') and vary consultation routing.",
		"computational_definition": "Accuracy of expertise-location beliefs, sharedness across actors, and consultation success rate.",
		"measurement_function": "",
		"required_events": "memory_query, memory_retrieval, agent_message_sent",
		"validity_notes": (
			"Not implemented at all, honestly: no expertise-belief modeling exists anywhere in "
			"the system. 'shared' remains an unimplemented EORL Memory Profile backend (V2 "
			"section 32.2 calls it P2) -- this construct has no manipulation surface to measure "
			"yet, not just a missing metric function."
		),
	},
	{
		"construct_name": "Routine coherence",
		"level_of_analysis": "process",
		"theoretical_definition": "The degree to which an organizational routine's enactment is stable and self-similar across repetitions -- the same actors doing the same kind of work in the same order.",
		"manipulation_strategy": "Vary coordination_mode (specialist_handoff vs broad_autonomy) and regime shifts; compare actor continuity and path persistence before/after.",
		"computational_definition": "Actor continuity (fraction of consecutive actions performed by the same actor) over a run's canonical event trace.",
		"measurement_function": "eorl_lab.analysis.coherence.actor_continuity",
		"required_events": "tool_result, decision_parsed",
		"validity_notes": (
			"Implemented and tested since Milestone 7. Related measures in the same module -- "
			"same_actor_transition_rate, functional_continuity, stage_continuity, "
			"repeated_path_probability -- give complementary views of coherence but are not "
			"individually registered as separate EORL Construct entries yet."
		),
	},
	{
		"construct_name": "Adaptive repertoire",
		"level_of_analysis": "process",
		"theoretical_definition": "The diversity of viable action paths an organization has available, and its ability to activate previously-unused or novel viable paths after an environmental regime shift.",
		"manipulation_strategy": "Introduce an EORL Regime Shift partway through a run; compare pre-/post-shock path usage.",
		"computational_definition": "Shannon entropy over the set of viable (successful-outcome) process paths observed across a run's episodes.",
		"measurement_function": "eorl_lab.analysis.repertoire.viable_path_entropy",
		"required_events": "episode_outcome, tool_result",
		"validity_notes": (
			"Implemented and tested since Milestone 7, and empirically exercised by SOTA "
			"Milestone 1's ground-truth-driven quality exceptions (RUN-00012: unique_sequence_count "
			"2, sequence_entropy 0.353). Related measures in the same module -- "
			"proportion_repertoire_reused_after_shock, novel_viable_paths_after_shock, "
			"path_extinction_rate, concentration_in_top_k -- give complementary post-shock "
			"repertoire views but are not individually registered as separate EORL Construct "
			"entries yet."
		),
	},
]


def execute():
	for construct in CONSTRUCTS:
		if frappe.db.exists("EORL Construct", construct["construct_name"]):
			continue
		frappe.get_doc({"doctype": "EORL Construct", "version": "1.0", **construct}).insert(ignore_permissions=True)
	frappe.db.commit()
