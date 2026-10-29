from typing import List, Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab.erp.registry import get_tool
from eorl_lab.memory.factory import get_memory_store
from eorl_lab.observability.context import ExperimentContext
from eorl_lab.observability.events import emit_event
from eorl_lab.providers.base import ModelRequest
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.runtime import authority
from eorl_lab.scenarios.procurement import generate_case

# Explicit step limit per actor turn (spec section 13: "no run should
# hang indefinitely"). The broad-autonomy actor's single continuous turn
# (sense, create PO, sense PO, submit PO, create receipt, submit receipt,
# sense receipt, create invoice, submit invoice, create payment, submit
# payment = 11 steps) needs more headroom than any one specialist stage;
# the ceiling is a safety bound, not the expected length.
MAX_STEPS_PER_ACTOR_TURN = 15

_RESULT_ID_KEYS = ("purchase_order", "purchase_receipt", "purchase_invoice", "payment_entry")

# Memory domain used for every role in the procure-to-pay routine; a
# richer domain taxonomy (e.g. one per exception family) becomes relevant
# once the Scenario Studio's exception families exist.
MEMORY_DOMAIN = "procurement"


def _primary_result_id(result: dict):
	for key in _RESULT_ID_KEYS:
		if result.get(key):
			return result[key]
	return None


def _run_actor_turn(
	ctx: ExperimentContext,
	agent,
	provider,
	case: dict,
	handoff: dict,
	memory: Optional[List[dict]] = None,
) -> tuple[dict, bool, str]:
	"""Runs one persistent actor's turn: repeated decide -> authority
	check -> execute -> observe loop until the actor signals stop or the
	step cap is hit (loop/deadlock safety, spec section 13). Returns
	(scratch, success, failure_reason). `scratch` accumulates this actor's
	own tool results so later turns (and the next actor's handoff) can
	build on confirmed ERP state rather than agent narrative.

	`memory` is a pre-retrieved, already-ranked list of this actor's own
	past memory records (empty/None if memory is disabled or this is the
	first episode) -- retrieval and writing happen in the caller, which
	knows the run/episode/memory-profile context this function doesn't
	need."""

	tool_policy = frappe.get_doc("EORL Tool Policy", agent.tool_policy)
	available_tools = [row.tool_name for row in tool_policy.allowed_semantic_tools]

	scratch: dict = {}
	write_count = 0
	success = True
	failure_reason = None

	for step in range(MAX_STEPS_PER_ACTOR_TURN):
		request = ModelRequest(
			system_instructions=agent.initial_system_instructions or "",
			context={
				"organizational_role": agent.organizational_role,
				"case": case,
				"handoff": handoff,
				"scratch": scratch,
				"memory": memory or [],
			},
			available_tools=available_tools,
		)

		emit_event(
			ctx, "agent_context_built", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			payload={"step": step},
		)
		emit_event(
			ctx, "model_request", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			payload={"provider": "deterministic"},
		)

		response = provider.generate(request)

		emit_event(
			ctx, "model_response", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			payload={"provider": response.provider, "resolved_model": response.resolved_model},
		)

		decision = response.decision
		emit_event(ctx, "decision_parsed", actor_slot=agent.organizational_role, actor_instance_id=agent.name, payload=decision)

		tool_name = decision["intended_action"]
		tool_args = decision.get("tool_arguments") or {}

		emit_event(
			ctx, "tool_requested", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			target_type="tool", target_id=tool_name, payload=tool_args,
		)

		authority_decision = authority.evaluate(
			tool_policy_name=agent.tool_policy,
			tool_name=tool_name,
			tool_args={**tool_args, "_episode_write_count": write_count},
		)

		if not authority_decision.allowed:
			emit_event(
				ctx, "tool_denied", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="tool", target_id=tool_name, success=False, payload=authority_decision.as_dict(),
			)
			return scratch, False, authority_decision.reason_code

		emit_event(
			ctx, "tool_authorized", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			target_type="tool", target_id=tool_name, success=True, payload=authority_decision.as_dict(),
		)

		tool_fn = get_tool(tool_name)
		is_write = tool_name in authority.WRITE_TOOLS

		if is_write:
			emit_event(
				ctx, "erp_state_before", actor_slot=agent.organizational_role, target_type=tool_name,
				payload={"tool_args": tool_args},
			)

		try:
			result = tool_fn(**tool_args)
		except Exception as exc:
			# A failed tool call does not corrupt the trace already
			# recorded for this episode -- it becomes an observable
			# organizational-process failure, not a silent repair
			# (spec sections 9 / 28).
			emit_event(
				ctx, "error", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="tool", target_id=tool_name, success=False, payload={"error": str(exc)},
			)
			return scratch, False, str(exc)

		emit_event(
			ctx, "tool_result", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			target_type="tool", target_id=tool_name, success=True, payload=result,
		)

		scratch.update(result)

		if is_write:
			write_count += 1
			emit_event(
				ctx, "erp_mutation", actor_slot=agent.organizational_role, target_type=tool_name,
				target_id=_primary_result_id(result), success=True, payload=result,
			)
			emit_event(
				ctx, "erp_state_after", actor_slot=agent.organizational_role, target_type=tool_name,
				target_id=_primary_result_id(result), payload=result,
			)

		if decision.get("stop"):
			return scratch, success, failure_reason
	else:
		return scratch, False, "MAX_STEPS_EXCEEDED"


def _handoff(ctx: ExperimentContext, from_role: str, to_role: str, content: dict):
	"""Explicit, observable inter-agent communication (spec section 15).
	For the specialist/handoff architecture (spec section 2.3 Architecture
	A), the handoff topology is enforced by the orchestrator itself, not
	left to agent discretion -- that is what "explicit handoffs across
	process stages; limited cross-stage autonomy" means for Architecture
	A. The broad-autonomy architecture (Architecture B) has no handoffs
	at all by construction: one actor, zero messages."""
	emit_event(ctx, "agent_message_sent", actor_slot=from_role, target_type="agent", target_id=to_role, payload=content)
	emit_event(ctx, "agent_message_received", actor_slot=to_role, target_type="agent", target_id=from_role, payload=content)


def _summarize_actor_action(role: str, scratch: dict) -> str:
	"""A short, role-specific action summary for the memory record (spec
	section 14's `action` field). Kept separate from the raw tool-result
	`scratch` dict so memory records stay human-scannable rather than
	dumping full ERP payloads into every row (the full payload is still
	available via payload_json)."""
	if role in ("Purchasing Agent", "General Purchasing Agent") and scratch.get("purchase_order"):
		return f"ordered_from:{scratch.get('supplier')}"
	if role == "Purchasing Manager Agent" and scratch.get("purchase_order_submitted"):
		return f"approved:{scratch.get('purchase_order')}"
	if role == "Warehouse Agent" and scratch.get("purchase_receipt_submitted"):
		return f"received:{scratch.get('purchase_receipt')}"
	if role == "Accounts Payable Agent" and scratch.get("payment_entry_submitted"):
		return f"paid:{scratch.get('payment_entry')}"
	if role == "General Purchasing Agent" and scratch.get("payment_entry_submitted"):
		return f"paid:{scratch.get('payment_entry')}"
	return "no_completed_action"


def _retrieve_memory(ctx: ExperimentContext, agent, run_name: str) -> List[dict]:
	memory_profile = frappe.get_doc("EORL Memory Profile", agent.memory_profile) if agent.memory_profile else None
	store = get_memory_store(memory_profile)
	k = (memory_profile.local_top_k if memory_profile else 0) or 3

	emit_event(
		ctx, "memory_query", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
		payload={"domain": MEMORY_DOMAIN, "k": k},
	)
	retrieved = store.retrieve(run=run_name, actor=agent.name, domain=MEMORY_DOMAIN, k=k)
	emit_event(
		ctx, "memory_retrieval", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
		payload={"count": len(retrieved), "records": [r.get("name") for r in retrieved]},
	)
	return retrieved


def _write_memory(ctx: ExperimentContext, agent, run_name: str, episode_name: str, case: dict, scratch: dict, success: bool):
	memory_profile = frappe.get_doc("EORL Memory Profile", agent.memory_profile) if agent.memory_profile else None
	store = get_memory_store(memory_profile)

	action = _summarize_actor_action(agent.organizational_role, scratch)
	record = store.write(
		{
			"run": run_name,
			"episode": episode_name,
			"actor": agent.name,
			"domain": MEMORY_DOMAIN,
			"case_summary": case.get("case_id"),
			"action": action,
			"outcome": "success" if success else "failure",
			"success": 1 if success else 0,
			"salience": 1.0,
			"payload_json": frappe.as_json(scratch),
		}
	)
	emit_event(
		ctx, "memory_write", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
		target_type="EORL Memory Record", target_id=record.get("name"),
		payload={"action": action, "success": success},
	)


def run_demo_episode(agent_template_name: str, seed: int = 42) -> dict:
	"""Milestone 2 vertical slice, kept for backward compatibility and its
	existing tests: one deterministic actor, one procurement case, one
	authority-checked tool call, full event trace, episode completion."""

	agent = frappe.get_doc("EORL Agent Template", agent_template_name)

	run = frappe.get_doc(
		{
			"doctype": "EORL Run",
			"run_seed": seed,
			"status": "running",
			"started_at": now_datetime(),
			"frappe_version": frappe.__version__,
		}
	).insert(ignore_permissions=True)

	ctx = ExperimentContext(run_id=run.name)
	emit_event(ctx, "run_initialized", payload={"run": run.name, "seed": seed, "agent_template": agent_template_name})

	episode = frappe.get_doc(
		{
			"doctype": "EORL Episode",
			"run": run.name,
			"episode_number": 1,
			"phase": "warmup",
			"status": "running",
			"started_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	ctx.episode_id = episode.name

	case = generate_case(seed=seed, episode=1)
	episode.scenario_case_id = case["case_id"]
	episode.ground_truth_json = frappe.as_json(case["latent_ground_truth"])
	episode.save(ignore_permissions=True)

	emit_event(ctx, "episode_initialized", payload={"episode": episode.name, "case_id": case["case_id"]})
	emit_event(ctx, "environment_observed", payload={"case": case})

	provider = DeterministicProvider()
	scratch, success, failure_reason = _run_actor_turn(ctx, agent, provider, case, handoff={})

	outcome = {
		"success": success,
		"purchase_order": scratch.get("purchase_order") if success else None,
	}
	if not success:
		outcome["failure_reason"] = failure_reason

	episode.status = "completed" if success else "failed"
	episode.success = 1 if success else 0
	episode.outcome_json = frappe.as_json(outcome)
	episode.ended_at = now_datetime()
	episode.save(ignore_permissions=True)

	emit_event(ctx, "episode_outcome", payload=outcome, success=success)

	run.status = "completed" if success else "failed"
	run.ended_at = now_datetime()
	run.current_episode = 1
	if not success:
		run.failure_reason = failure_reason
	run.save(ignore_permissions=True)

	emit_event(ctx, "run_completed", payload={"status": run.status})
	run.event_count = frappe.db.count("EORL Event", {"run": run.name})
	run.save(ignore_permissions=True)

	return {"run": run.name, "episode": episode.name, "outcome": outcome, "event_count": run.event_count}


# role name -> (slot_map dict key, handoff builder from accumulated routine_state)
_SPECIALIST_SEQUENCE = [
	("Purchasing Agent", "purchasing_agent", lambda state: {}),
	("Purchasing Manager Agent", "purchasing_manager_agent", lambda state: {"purchase_order": state["purchase_order"]}),
	("Warehouse Agent", "warehouse_agent", lambda state: {"purchase_order": state["purchase_order"]}),
	("Accounts Payable Agent", "accounts_payable_agent", lambda state: {"purchase_receipt": state["purchase_receipt"]}),
]


def _run_specialist_episode(ctx: ExperimentContext, slot_map: dict, case: dict, provider) -> dict:
	"""Architecture A (specialist/handoff, spec section 2.3): four
	persistent actor slots, each restricted to its own tools, hand off
	one full procure-to-pay routine with explicit, logged communication
	between stages. `slot_map` maps the slot keys in _SPECIALIST_SEQUENCE
	to EORL Agent Template names."""
	routine_state: dict = {}
	outcome = {"success": False, "stage_results": {}}

	previous_role = None
	completed_all_stages = True

	for role_name, slot_key, handoff_fn in _SPECIALIST_SEQUENCE:
		agent_template_name = slot_map[slot_key]
		agent = frappe.get_doc("EORL Agent Template", agent_template_name)

		try:
			handoff = handoff_fn(routine_state)
		except KeyError as exc:
			outcome["failure_reason"] = f"cannot hand off to {role_name}: missing {exc} from prior stage"
			completed_all_stages = False
			break

		if previous_role is not None:
			_handoff(ctx, previous_role, role_name, {"handoff": handoff})

		retrieved_memory = _retrieve_memory(ctx, agent, ctx.run_id)
		stage_scratch, stage_success, stage_failure_reason = _run_actor_turn(
			ctx, agent, provider, case, handoff, memory=retrieved_memory
		)
		_write_memory(ctx, agent, ctx.run_id, ctx.episode_id, case, stage_scratch, stage_success)

		routine_state.update(stage_scratch)
		outcome["stage_results"][role_name] = stage_scratch

		if not stage_success:
			outcome["failure_reason"] = stage_failure_reason
			completed_all_stages = False
			break

		previous_role = role_name

	outcome["success"] = completed_all_stages
	outcome["purchase_order"] = routine_state.get("purchase_order")
	outcome["purchase_receipt"] = routine_state.get("purchase_receipt")
	outcome["purchase_invoice"] = routine_state.get("purchase_invoice")
	outcome["payment_entry"] = routine_state.get("payment_entry")
	return outcome


def _run_broad_autonomy_episode(ctx: ExperimentContext, slot_map: dict, case: dict, provider) -> dict:
	"""Architecture B (broad autonomy, spec section 2.3): one actor
	performs every stage of the same routine itself, with zero handoffs
	-- "fewer mandatory handoffs; greater actor continuity" by
	construction, using the same underlying decision rules as the
	specialists (see providers.deterministic._choose_supplier) so the two
	architectures are comparable rather than differing in what the
	"right" decision even is."""
	agent_template_name = slot_map["general_purchasing_agent"]
	agent = frappe.get_doc("EORL Agent Template", agent_template_name)

	retrieved_memory = _retrieve_memory(ctx, agent, ctx.run_id)
	scratch, success, failure_reason = _run_actor_turn(ctx, agent, provider, case, handoff={}, memory=retrieved_memory)
	_write_memory(ctx, agent, ctx.run_id, ctx.episode_id, case, scratch, success)

	outcome = {
		"success": success,
		"stage_results": {"General Purchasing Agent": scratch},
		"purchase_order": scratch.get("purchase_order"),
		"purchase_receipt": scratch.get("purchase_receipt"),
		"purchase_invoice": scratch.get("purchase_invoice"),
		"payment_entry": scratch.get("payment_entry"),
	}
	if not success:
		outcome["failure_reason"] = failure_reason
	return outcome


def run_specialist_routine(agent_templates: dict, seed: int = 42, episode_count: int = 1) -> dict:
	"""Milestone 3's Architecture A entrypoint, kept for backward
	compatibility and its existing tests. `run_architecture` (below) is
	the config-driven entrypoint Milestone 5 adds; this function now
	delegates its per-episode logic to the same `_run_specialist_episode`
	helper `run_architecture` uses, so there is one specialist-handoff
	implementation, not two."""

	run = frappe.get_doc(
		{
			"doctype": "EORL Run",
			"run_seed": seed,
			"status": "running",
			"started_at": now_datetime(),
			"frappe_version": frappe.__version__,
			"architecture_snapshot_json": frappe.as_json({"architecture": "specialist_handoff", "agents": agent_templates}),
			"agent_snapshots_json": frappe.as_json(_snapshot_agent_templates(agent_templates)),
		}
	).insert(ignore_permissions=True)

	ctx = ExperimentContext(run_id=run.name)
	emit_event(
		ctx, "run_initialized",
		payload={
			"run": run.name, "seed": seed, "architecture": "specialist_handoff",
			"agents": agent_templates, "episode_count": episode_count,
		},
	)

	episode_outcomes = _run_episode_loop(ctx, run, agent_templates, seed, episode_count, "specialist_handoff", regime_shift=None)

	last_outcome = episode_outcomes[-1] if episode_outcomes else {"success": False}
	return {
		"run": run.name,
		"episodes": episode_outcomes,
		"outcome": last_outcome,
		"event_count": run.event_count,
	}


def _snapshot_agent_templates(slot_map: dict) -> dict:
	"""Resolve + snapshot each bound template at run start (spec section
	8.4): "resolve templates; snapshot prompts; snapshot model profiles;
	snapshot tool policies". Immutable for the life of the run even if the
	underlying EORL Agent Template document is edited afterwards."""
	snapshot = {}
	for slot_key, template_name in slot_map.items():
		agent = frappe.get_doc("EORL Agent Template", template_name)
		snapshot[slot_key] = {
			"template": agent.name,
			"organizational_role": agent.organizational_role,
			"model_profile": agent.model_profile,
			"memory_profile": agent.memory_profile,
			"tool_policy": agent.tool_policy,
			"initial_system_instructions": agent.initial_system_instructions,
		}
	return snapshot


def _run_episode_loop(
	ctx: ExperimentContext,
	run,
	slot_map: dict,
	seed: int,
	episode_count: int,
	coordination_mode: str,
	regime_shift: Optional[dict],
) -> list:
	"""Shared multi-episode driver for both coordination modes. A failed
	episode halts the run (spec section 13: a failure state, not a
	silently-skipped one)."""
	episode_outcomes = []
	run_success = True
	run_failure_reason = None
	provider = DeterministicProvider()

	for episode_number in range(1, episode_count + 1):
		episode = frappe.get_doc(
			{
				"doctype": "EORL Episode",
				"run": run.name,
				"episode_number": episode_number,
				"phase": _phase_for_episode(episode_number, regime_shift),
				"status": "running",
				"started_at": now_datetime(),
			}
		).insert(ignore_permissions=True)
		ctx.episode_id = episode.name

		case = generate_case(seed=seed, episode=episode_number, regime_shift=regime_shift)
		episode.scenario_case_id = case["case_id"]
		episode.ground_truth_json = frappe.as_json(case["latent_ground_truth"])
		episode.save(ignore_permissions=True)

		emit_event(ctx, "episode_initialized", payload={"episode": episode.name, "case_id": case["case_id"]})
		emit_event(ctx, "environment_observed", payload={"case": case})

		if coordination_mode == "specialist_handoff":
			outcome = _run_specialist_episode(ctx, slot_map, case, provider)
		elif coordination_mode == "broad_autonomy":
			outcome = _run_broad_autonomy_episode(ctx, slot_map, case, provider)
		else:
			raise ValueError(f"Unknown coordination_mode: {coordination_mode!r}")

		outcome["episode_number"] = episode_number

		episode.status = "completed" if outcome["success"] else "failed"
		episode.success = 1 if outcome["success"] else 0
		episode.outcome_json = frappe.as_json(outcome)
		episode.ended_at = now_datetime()
		episode.save(ignore_permissions=True)

		emit_event(ctx, "episode_outcome", payload=outcome, success=outcome["success"])
		episode_outcomes.append(outcome)

		run.current_episode = episode_number
		run.save(ignore_permissions=True)

		if not outcome["success"]:
			run_success = False
			run_failure_reason = outcome.get("failure_reason")
			break  # spec section 13: a failed episode is a failure state, not silently skipped

	run.status = "completed" if run_success else "failed"
	run.ended_at = now_datetime()
	if not run_success:
		run.failure_reason = run_failure_reason
	run.save(ignore_permissions=True)

	emit_event(ctx, "run_completed", payload={"status": run.status, "episodes_completed": len(episode_outcomes)})
	run.event_count = frappe.db.count("EORL Event", {"run": run.name})
	run.save(ignore_permissions=True)

	return episode_outcomes


def _phase_for_episode(episode_number: int, regime_shift: Optional[dict]) -> str:
	if regime_shift and episode_number >= regime_shift.get("trigger_episode", float("inf")):
		return "shock"
	return "stable" if episode_number > 1 else "warmup"


def run_architecture(
	architecture_name: str,
	seed: int = 42,
	episode_count: int = 1,
	regime_shift: Optional[str] = None,
) -> dict:
	"""Milestone 5's config-driven entrypoint (spec section 26: "Add...
	architecture selection through config only"). Reads an EORL
	Architecture document's `coordination_mode` and `actor_slots` to
	decide HOW the routine runs -- the caller never names a Python
	function per architecture. An optional EORL Regime Shift (by name)
	changes environmental parameters starting at its trigger_episode,
	hidden from agents (spec section 2.4); the same seed given to two
	different architectures produces the byte-identical scenario stream
	per episode (spec section 18's paired seeds), since `generate_case`
	is a pure function of (seed, episode, regime_shift) independent of
	which architecture calls it."""

	architecture = frappe.get_doc("EORL Architecture", architecture_name)
	slot_map = {row.slot_id: row.agent_template for row in architecture.actor_slots}

	regime_shift_payload = None
	if regime_shift:
		shift_doc = frappe.get_doc("EORL Regime Shift", regime_shift)
		regime_shift_payload = {
			"trigger_episode": shift_doc.trigger_episode,
			"parameter_delta_json": frappe.parse_json(shift_doc.parameter_delta_json or "{}"),
		}

	run = frappe.get_doc(
		{
			"doctype": "EORL Run",
			"run_seed": seed,
			"status": "running",
			"started_at": now_datetime(),
			"frappe_version": frappe.__version__,
			"architecture_snapshot_json": frappe.as_json(architecture.as_dict()),
			"agent_snapshots_json": frappe.as_json(_snapshot_agent_templates(slot_map)),
			"regime_shift_snapshot_json": frappe.as_json(regime_shift_payload) if regime_shift_payload else None,
		}
	).insert(ignore_permissions=True)

	ctx = ExperimentContext(run_id=run.name)
	emit_event(
		ctx, "run_initialized",
		payload={
			"run": run.name, "seed": seed, "architecture": architecture.name,
			"coordination_mode": architecture.coordination_mode, "slot_map": slot_map,
			"episode_count": episode_count, "regime_shift": regime_shift,
		},
	)

	episode_outcomes = _run_episode_loop(
		ctx, run, slot_map, seed, episode_count, architecture.coordination_mode, regime_shift_payload
	)

	last_outcome = episode_outcomes[-1] if episode_outcomes else {"success": False}
	return {
		"run": run.name,
		"architecture": architecture.name,
		"coordination_mode": architecture.coordination_mode,
		"episodes": episode_outcomes,
		"outcome": last_outcome,
		"event_count": run.event_count,
	}
