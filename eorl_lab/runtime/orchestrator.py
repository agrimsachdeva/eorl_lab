import inspect
import time
from typing import Callable, List, Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab import routines
from eorl_lab.erp.registry import get_tool
from eorl_lab.memory.factory import get_memory_store
from eorl_lab.observability.context import ExperimentContext
from eorl_lab.observability.events import emit_event
from eorl_lab.providers.base import ModelRequest
from eorl_lab.providers.factory import engine_type_of, get_provider_for_agent
from eorl_lab.runtime import authority
from eorl_lab.scenarios.procurement import DEFAULT_OUTCOME_MODEL, generate_case

# Explicit step limit per actor turn (spec section 13: "no run should
# hang indefinitely"). The broad-autonomy actor's single continuous turn,
# worst case (quality exception: inspect + escalate + message, on top of
# the full happy-path chain), now runs 14 steps -- bumped from 15 to 18
# for real margin, not just clearing the bar. It is a safety bound, not
# the expected length.
MAX_STEPS_PER_ACTOR_TURN = 18

_RESULT_ID_KEYS = ("purchase_order", "purchase_receipt", "purchase_invoice", "payment_entry")

# Memory domain used for every role in the procure-to-pay routine; a
# richer domain taxonomy (e.g. one per exception family) becomes relevant
# once the Scenario Studio's exception families exist.
MEMORY_DOMAIN = "procurement"


# Run failure taxonomy (submission-day plan section 25).
FAILURE_TYPES = (
	"model_timeout", "model_parse_error", "tool_error", "erp_validation_error",
	"authority_denial_expected", "authority_denial_unexpected", "infrastructure_error",
	"terminal_condition_not_met", "max_turns_exceeded",
)
RETRYABLE_FAILURE_TYPES = {"model_timeout", "model_parse_error", "infrastructure_error"}


def _classify_provider_failure(exc: Exception) -> str:
	message = str(exc).lower()
	if "timed out" in message or "timeout" in message:
		return "model_timeout"
	if "no tool call" in message or "invalid json" in message or "finish_reason" in message:
		return "model_parse_error"
	return "infrastructure_error"


def _classify_tool_failure(exc: Exception) -> str:
	if isinstance(exc, frappe.ValidationError):
		return "erp_validation_error"
	return "tool_error"


def _cancel_requested(run_name: str) -> bool:
	"""Cancellation is signalled through the cache rather than the run row,
	because a long run holds one open transaction and would not see a
	status change committed by another request."""
	return bool(frappe.cache().get_value(f"eorl_cancel:{run_name}"))


def _primary_result_id(result: dict):
	for key in _RESULT_ID_KEYS:
		if result.get(key):
			return result[key]
	return None


def _call_tool_with_context(tool_fn, tool_args: dict, *, case: dict, sender_slot: str, communication_policy: Optional[str]):
	"""SOTA Milestone 1: injects environment/organization context into
	only the tools that declare it by parameter name -- `_case` (ground
	truth, V2 section 15), `_sender_slot` and `_communication_policy`
	(V2 section 9). None of the 11 tools built through Milestone 5
	declare any of these, so this is a no-op for them; only
	eorl_lab.erp.stock.inspect_received_goods and
	eorl_lab.organization.communication.message_agent opt in. An agent's
	own decision arguments can never supply these names (they're not in
	`tool_args` to begin with), so an agent cannot forge its own
	identity or policy."""
	sig = inspect.signature(tool_fn)
	extra = {}
	if "_case" in sig.parameters:
		extra["_case"] = case
	if "_sender_slot" in sig.parameters:
		extra["_sender_slot"] = sender_slot
	if "_communication_policy" in sig.parameters:
		extra["_communication_policy"] = communication_policy
	return tool_fn(**tool_args, **extra)


def _run_actor_turn(
	ctx: ExperimentContext,
	agent,
	provider,
	case: dict,
	handoff: dict,
	memory: Optional[List[dict]] = None,
	communication_policy: Optional[str] = None,
	tool_gate: Optional[Callable[[dict], Optional[set]]] = None,
) -> tuple:
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
	need. `communication_policy` (SOTA Milestone 1) is the EORL
	Communication Policy name this run's architecture is bound to, if
	any -- passed through to tools that need it (message_agent), never
	read directly here.

	Submission-day additions. Returns (scratch, success, failure_reason,
	failure_type). `tool_gate`, when given, maps the actor's scratch to
	the set of tools its current stage allows (the matched-tool-ecology
	broad-autonomy condition). Gated-out tools are neither offered to the
	actor nor authorized if it asks for them anyway; the check runs here,
	outside the model, like every other authority check."""

	tool_policy = frappe.get_doc("EORL Tool Policy", agent.tool_policy)
	policy_tools = [row.tool_name for row in tool_policy.allowed_semantic_tools]

	scratch: dict = {}
	write_count = 0
	success = True
	failure_reason = None

	for step in range(MAX_STEPS_PER_ACTOR_TURN):
		gate = tool_gate(scratch) if tool_gate else None
		available_tools = [t for t in policy_tools if gate is None or t in gate]
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
			payload={"provider": provider.__class__.__name__},
		)

		started = time.monotonic()
		try:
			response = provider.generate(request)
		except Exception as exc:
			# SOTA Milestone 3: a real network-calling provider can fail in
			# ways DeterministicProvider never could (timeout, malformed
			# tool call, no tool call returned) -- that is an observable
			# organizational-process failure, not a crash that should take
			# the whole run down uncaught (spec sections 9/28, the same
			# principle the tool-execution except block below already
			# follows).
			emit_event(
				ctx, "error", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="provider", success=False, payload={"error": str(exc)},
			)
			return scratch, False, str(exc), _classify_provider_failure(exc)

		latency_ms = response.latency_ms if response.latency_ms is not None else (time.monotonic() - started) * 1000.0
		usage = response.token_counts or {}
		telemetry = ctx.telemetry
		telemetry["model_calls"] += 1
		telemetry["input_tokens"] += usage.get("prompt_tokens") or 0
		telemetry["output_tokens"] += usage.get("completion_tokens") or 0
		telemetry["total_tokens"] += usage.get("total_tokens") or 0
		telemetry["retries"] += response.retry_count or 0
		telemetry["latency_ms"] += latency_ms

		emit_event(
			ctx, "model_response", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			payload={
				"provider": response.provider, "resolved_model": response.resolved_model,
				# The profile name, not its base_url: events are readable by
				# the reviewer role and the endpoint address is not public.
				"model_profile": agent.model_profile,
				"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
				"latency_ms": round(latency_ms, 1), "retry_count": response.retry_count or 0,
			},
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
		if authority_decision.allowed and gate is not None and tool_name not in gate:
			authority_decision = authority.AuthorityDecision(
				False, "STAGE_GATED", authority_decision.policy_version, {"allowed_at_this_stage": sorted(gate)}
			)

		if not authority_decision.allowed:
			emit_event(
				ctx, "tool_denied", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="tool", target_id=tool_name, success=False, payload=authority_decision.as_dict(),
			)
			expected = authority_decision.reason_code in ctx.expected_denial_codes
			return scratch, False, authority_decision.reason_code, (
				"authority_denial_expected" if expected else "authority_denial_unexpected"
			)

		emit_event(
			ctx, "tool_authorized", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
			target_type="tool", target_id=tool_name, success=True, payload=authority_decision.as_dict(),
		)

		if authority_decision.soft_violations:
			# V2 section 13: a soft rule never blocks execution -- it's
			# logged as its own observable event alongside the normal
			# authorization, not instead of it.
			emit_event(
				ctx, "soft_rule_violation", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="tool", target_id=tool_name, success=True,
				payload={"violations": authority_decision.soft_violations, "tool_args": tool_args},
			)

		tool_fn = get_tool(tool_name)
		is_write = tool_name in authority.WRITE_TOOLS
		is_communication = tool_name in authority.COMMUNICATION_TOOLS

		if is_write:
			emit_event(
				ctx, "erp_state_before", actor_slot=agent.organizational_role, target_type=tool_name,
				payload={"tool_args": tool_args},
			)

		try:
			result = _call_tool_with_context(
				tool_fn, tool_args,
				case=case, sender_slot=agent.organizational_role, communication_policy=communication_policy,
			)
		except Exception as exc:
			# A failed tool call does not corrupt the trace already
			# recorded for this episode -- it becomes an observable
			# organizational-process failure, not a silent repair
			# (spec sections 9 / 28).
			emit_event(
				ctx, "error", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
				target_type="tool", target_id=tool_name, success=False, payload={"error": str(exc)},
			)
			return scratch, False, str(exc), _classify_tool_failure(exc)

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

		if is_communication and result.get("delivered"):
			# Agent-chosen messaging (V2 section 9) uses the same two
			# event types the orchestrator-enforced structural handoffs
			# use -- both are real inter-agent messages, just decided
			# by a different party.
			emit_event(
				ctx, "agent_message_sent", actor_slot=agent.organizational_role,
				target_type="agent", target_id=result.get("recipient"), payload={"content": result.get("content")},
			)
			emit_event(
				ctx, "agent_message_received", actor_slot=result.get("recipient"),
				target_type="agent", target_id=agent.organizational_role, payload={"content": result.get("content")},
			)

		if decision.get("stop"):
			return scratch, success, failure_reason, None
	else:
		return scratch, False, "MAX_STEPS_EXCEEDED", "max_turns_exceeded"


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


def _record_task_assignment(ctx: ExperimentContext, slot_id: str, agent_template_name: str):
	"""V2 section 11: task assignment is a real, logged decision, not an
	implicit default. SOTA Milestone 1 scope: every architecture built
	so far has exactly one candidate per slot, so this always records
	policy "fixed" with candidate_count=1 -- the data model and event are
	real even though multi-candidate pooling (choosing among several
	agents for one slot) isn't built yet (see SOTA_ROADMAP.md)."""
	doc = frappe.get_doc(
		{
			"doctype": "EORL Task Assignment",
			"run": ctx.run_id,
			"episode": ctx.episode_id,
			"slot_id": slot_id,
			"assigned_to": agent_template_name,
			"assignment_policy": "fixed",
			"candidate_count": 1,
			"rationale": "only one candidate configured for this slot",
			"assigned_at": now_datetime(),
		}
	).insert(ignore_permissions=True)
	emit_event(
		ctx, "task_assigned", target_type="EORL Task Assignment", target_id=doc.name,
		payload={"slot_id": slot_id, "assigned_to": agent_template_name, "policy": "fixed"},
	)
	return doc.name


def _summarize_actor_action(role: str, scratch: dict) -> str:
	"""A short, role-specific action summary for the memory record (spec
	section 14's `action` field). Kept separate from the raw tool-result
	`scratch` dict so memory records stay human-scannable rather than
	dumping full ERP payloads into every row (the full payload is still
	available via payload_json).

	An actor that ordered and also observed the inspection itself (only
	the broad-autonomy actor does) gets ";quality:passed" or
	";quality:failed" appended, so its own memory carries the feedback it
	actually saw. A specialist Purchasing Agent never sees the inspection,
	and its record says only whom it ordered from."""
	if role in ("Purchasing Agent", "General Purchasing Agent") and scratch.get("purchase_order"):
		action = f"ordered_from:{scratch.get('supplier')}"
		if "quality_passed" in scratch:
			action += ";quality:" + ("passed" if scratch["quality_passed"] else "failed")
		return action
	if role == "Purchasing Manager Agent" and scratch.get("purchase_order_submitted"):
		return f"approved:{scratch.get('purchase_order')}"
	if role == "Warehouse Agent" and scratch.get("purchase_receipt_submitted"):
		return f"received:{scratch.get('purchase_receipt')}"
	if role == "Accounts Payable Agent" and scratch.get("payment_entry_submitted"):
		return f"paid:{scratch.get('payment_entry')}"
	if role == "General Purchasing Agent" and scratch.get("payment_entry_submitted"):
		return f"paid:{scratch.get('payment_entry')}"
	completed = [k[: -len("_submitted")] for k, v in scratch.items() if k.endswith("_submitted") and v]
	if completed:
		return "completed:" + ",".join(completed)
	return "no_completed_action"


def _retrieve_memory(ctx: ExperimentContext, agent, run_name: str, domain: str = MEMORY_DOMAIN) -> List[dict]:
	memory_profile = frappe.get_doc("EORL Memory Profile", agent.memory_profile) if agent.memory_profile else None
	store = get_memory_store(memory_profile)
	k = (memory_profile.local_top_k if memory_profile else 0) or 3

	emit_event(
		ctx, "memory_query", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
		payload={"domain": domain, "k": k},
	)
	retrieved = store.retrieve(run=run_name, actor=agent.name, domain=domain, k=k)
	emit_event(
		ctx, "memory_retrieval", actor_slot=agent.organizational_role, actor_instance_id=agent.name,
		payload={"count": len(retrieved), "records": [r.get("name") for r in retrieved]},
	)
	return retrieved


def _write_memory(ctx: ExperimentContext, agent, run_name: str, episode_name: str, case: dict, scratch: dict, success: bool, domain: str = MEMORY_DOMAIN):
	memory_profile = frappe.get_doc("EORL Memory Profile", agent.memory_profile) if agent.memory_profile else None
	store = get_memory_store(memory_profile)

	action = _summarize_actor_action(agent.organizational_role, scratch)
	record = store.write(
		{
			"run": run_name,
			"episode": episode_name,
			"actor": agent.name,
			"domain": domain,
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

	provider = get_provider_for_agent(agent)
	scratch, success, failure_reason, _failure_type = _run_actor_turn(ctx, agent, provider, case, handoff={})

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


def _episode_outcome(routine: dict, routine_state: dict, success: bool, failure_reason=None, failure_type=None) -> dict:
	"""The episode outcome common to both architectures, including the
	terminal-condition check and outcome utility v1."""
	outcome = {"success": success, "stage_results": {}}
	for key in routine["outcome_keys"]:
		outcome[key] = routine_state.get(key)
	if success:
		unmet = [k for k in routine["terminal_conditions"] if not routine_state.get(k)]
		if unmet:
			outcome["success"] = False
			failure_reason = f"terminal condition not met: {', '.join(unmet)}"
			failure_type = "terminal_condition_not_met"
	if outcome["success"]:
		total = routine_state.get("units_total") or 0
		rejected = routine_state.get("units_rejected") or 0 if routine_state.get("quality_passed") is False else 0
		outcome["utility"] = 1.0 - (rejected / total if total else 0.0)
	else:
		outcome["utility"] = 0.0
		outcome["failure_reason"] = failure_reason
		outcome["failure_type"] = failure_type
	return outcome


def _run_specialist_episode(
	ctx: ExperimentContext, slot_map: dict, case: dict, communication_policy: Optional[str] = None,
	routine: Optional[dict] = None, engine_override: Optional[str] = None,
) -> dict:
	"""Architecture A (specialist/handoff, spec section 2.3): one
	persistent actor per stage of the routine, each restricted to its own
	tools, handing off with explicit, logged communication between
	stages. `slot_map` maps the routine's stage slots to EORL Agent
	Template names.

	The stage order, the slot names and what each stage hands on come
	from the routine template (eorl_lab.routines), so the same function
	runs procure-to-pay and order-to-cash.

	SOTA Milestone 3: each slot resolves its OWN model provider from its
	own EORL Agent Template's model_profile (get_provider_for_agent) --
	a run is no longer forced to use one single provider instance for
	every actor; a specialist_handoff run can genuinely mix a real
	LLM-backed Purchasing Agent with deterministic specialists elsewhere
	in the chain, or any other combination."""
	routine = routine or routines.resolve_routine()
	routine_state: dict = {}
	stage_results = {}
	previous_role = None
	success, failure_reason, failure_type = True, None, None

	for stage in routine["stages"]:
		role_name, slot_key = stage["role"], stage["slot"]
		agent_template_name = slot_map[slot_key]
		_record_task_assignment(ctx, slot_key, agent_template_name)
		agent = frappe.get_doc("EORL Agent Template", agent_template_name)
		provider = get_provider_for_agent(agent, engine_override)

		missing = [k for k in stage.get("handoff_keys") or [] if k not in routine_state]
		if missing:
			success = False
			failure_reason = f"cannot hand off to {role_name}: missing {missing} from prior stage"
			failure_type = "terminal_condition_not_met"
			break
		handoff = {k: routine_state[k] for k in stage.get("handoff_keys") or []}

		if previous_role is not None:
			_handoff(ctx, previous_role, role_name, {"handoff": handoff})

		retrieved_memory = _retrieve_memory(ctx, agent, ctx.run_id, routine["memory_domain"])
		stage_scratch, stage_success, stage_failure_reason, stage_failure_type = _run_actor_turn(
			ctx, agent, provider, case, handoff, memory=retrieved_memory, communication_policy=communication_policy
		)
		_write_memory(ctx, agent, ctx.run_id, ctx.episode_id, case, stage_scratch, stage_success, routine["memory_domain"])

		routine_state.update(stage_scratch)
		stage_results[role_name] = stage_scratch

		if not stage_success:
			success, failure_reason, failure_type = False, stage_failure_reason, stage_failure_type
			break

		previous_role = role_name

	outcome = _episode_outcome(routine, routine_state, success, failure_reason, failure_type)
	outcome["stage_results"] = stage_results
	return outcome


def _stage_gate(routine: dict) -> Callable[[dict], set]:
	"""For the matched-tool-ecology condition: the tools of the first
	stage whose completion key is not yet in the actor's scratch, plus
	finish_turn. Once every stage is complete, only finish_turn."""
	def gate(scratch: dict) -> set:
		for stage in routine["stages"]:
			if not scratch.get(stage["completes_on"]):
				return set(stage["tools"]) | {"finish_turn"}
		return {"finish_turn"}
	return gate


def _run_broad_autonomy_episode(
	ctx: ExperimentContext, slot_map: dict, case: dict, communication_policy: Optional[str] = None,
	routine: Optional[dict] = None, engine_override: Optional[str] = None, stage_gated: bool = False,
) -> dict:
	"""Architecture B (broad autonomy, spec section 2.3): one actor
	performs every stage of the same routine itself, with zero handoffs
	-- "fewer mandatory handoffs; greater actor continuity" by
	construction. When using DeterministicProvider this follows the same
	underlying decision rules as the specialists (see
	providers.deterministic._choose_supplier) so the two architectures
	are comparable rather than differing in what the "right" decision
	even is; a real model provider makes its own decisions instead.
	SOTA Milestone 3: the provider is resolved from this slot's own
	agent template (get_provider_for_agent), not forced by the caller.

	`stage_gated` (submission-day plan section 8) is the matched-tool-
	ecology variant: the one actor is offered, step by step, only the
	tools the specialist for the current stage would hold."""
	routine = routine or routines.resolve_routine()
	slot_key = routine["broad_slot"] if routine["broad_slot"] in slot_map else next(iter(slot_map))
	agent_template_name = slot_map[slot_key]
	_record_task_assignment(ctx, slot_key, agent_template_name)
	agent = frappe.get_doc("EORL Agent Template", agent_template_name)
	provider = get_provider_for_agent(agent, engine_override)

	retrieved_memory = _retrieve_memory(ctx, agent, ctx.run_id, routine["memory_domain"])
	scratch, success, failure_reason, failure_type = _run_actor_turn(
		ctx, agent, provider, case, handoff={}, memory=retrieved_memory, communication_policy=communication_policy,
		tool_gate=_stage_gate(routine) if stage_gated else None,
	)
	_write_memory(ctx, agent, ctx.run_id, ctx.episode_id, case, scratch, success, routine["memory_domain"])

	outcome = _episode_outcome(routine, scratch, success, failure_reason, failure_type)
	outcome["stage_results"] = {agent.organizational_role: scratch}
	return outcome


def run_specialist_routine(agent_templates: dict, seed: int = 42, episode_count: int = 1) -> dict:
	"""Milestone 3's Architecture A entrypoint, kept for backward
	compatibility and its existing tests. `run_architecture` (below) is
	the config-driven entrypoint Milestone 5 adds; this function now
	delegates its per-episode logic to the same `_run_specialist_episode`
	helper `run_architecture` uses, so there is one specialist-handoff
	implementation, not two. No EORL Communication Policy is bound here
	(there's no EORL Architecture document in this code path) -- a
	message_agent call made by a run launched this way will report
	NO_POLICY_BOUND rather than deliver, which is the same honest
	pre-Milestone-5 scoping eorl_lab.observability.replay.reproduce_run
	already documents."""

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
			# Submission-day additions: the resolved contents, so two runs'
			# manifests can be compared field by field (plan section 7)
			# without depending on the linked documents staying unedited.
			"model_profile_config": _profile_config("EORL Model Profile", agent.model_profile,
				("provider", "model_name", "temperature", "top_p", "max_tokens", "reasoning_mode_if_supported")),
			"memory_profile_config": _profile_config("EORL Memory Profile", agent.memory_profile,
				("local_memory_enabled", "local_backend", "local_top_k", "recency_weight", "outcome_weight", "similarity_weight")),
			"tool_policy_config": _tool_policy_config(agent.tool_policy),
		}
	return snapshot


def _profile_config(doctype: str, name: Optional[str], fields: tuple) -> Optional[dict]:
	if not name or not frappe.db.exists(doctype, name):
		return None
	doc = frappe.get_doc(doctype, name)
	return {f: doc.get(f) for f in fields}


def _tool_policy_config(name: Optional[str]) -> Optional[dict]:
	if not name or not frappe.db.exists("EORL Tool Policy", name):
		return None
	policy = frappe.get_doc("EORL Tool Policy", name)
	return {
		"tools": sorted(row.tool_name for row in policy.allowed_semantic_tools),
		**{f: policy.get(f) for f in (
			"may_submit_documents", "may_approve", "may_message_agents", "has_decision_authority",
			"has_assignment_authority", "max_write_actions_per_episode", "soft_rule_large_qty_threshold",
		)},
	}


def _run_episode_loop(
	ctx: ExperimentContext,
	run,
	slot_map: dict,
	seed: int,
	episode_count: int,
	coordination_mode: str,
	regime_shift: Optional[dict],
	communication_policy: Optional[str] = None,
	start_episode: int = 1,
	routine: Optional[dict] = None,
	outcome_model: str = DEFAULT_OUTCOME_MODEL,
	stage_gated: bool = False,
) -> list:
	"""Shared multi-episode driver for both coordination modes. A failed
	episode halts the run (spec section 13: a failure state, not a
	silently-skipped one). `start_episode` (SOTA Milestone 2) lets a
	branched run continue episode numbering from where its parent left
	off (branch_point_episode + 1) instead of always restarting at 1 --
	see branch_run() below.

	Submission-day additions: the scenario generator and the stage
	structure come from `routine`; every environment_observed event
	carries the exogenous state separately from the case; a cancellation
	request is honored between episodes; failure type and telemetry
	totals are written to the run."""
	routine = routine or routines.resolve_routine()
	case_fn = frappe.get_attr(routine["scenario_generator"])
	exogenous_fn = frappe.get_attr(routine["exogenous_state_function"]) if routine.get("exogenous_state_function") else None
	wallclock_started = time.monotonic()
	episode_outcomes = []
	run_success = True
	run_failure_reason = None
	run_failure_type = None
	cancelled = False

	for episode_number in range(start_episode, start_episode + episode_count):
		if _cancel_requested(run.name):
			cancelled = True
			break
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

		case = case_fn(seed=seed, episode=episode_number, regime_shift=regime_shift, outcome_model=outcome_model)
		episode.scenario_case_id = case["case_id"]
		episode.environmental_state_hash = case["case_hash"]
		episode.ground_truth_json = frappe.as_json(case["latent_ground_truth"])
		episode.save(ignore_permissions=True)

		emit_event(ctx, "episode_initialized", payload={"episode": episode.name, "case_id": case["case_id"]})
		emit_event(
			ctx, "environment_observed",
			payload={
				"case": case,
				"exogenous_state": exogenous_fn(case, regime_shift) if exogenous_fn else None,
				"endogenous_state_sources": list(_ENDOGENOUS_SOURCES),
			},
		)

		if coordination_mode == "specialist_handoff":
			outcome = _run_specialist_episode(
				ctx, slot_map, case, communication_policy=communication_policy, routine=routine, engine_override=ctx.engine_override,
			)
		elif coordination_mode == "broad_autonomy":
			outcome = _run_broad_autonomy_episode(
				ctx, slot_map, case, communication_policy=communication_policy, routine=routine,
				engine_override=ctx.engine_override, stage_gated=stage_gated,
			)
		else:
			raise ValueError(f"Unknown coordination_mode: {coordination_mode!r}")

		outcome["episode_number"] = episode_number

		episode.status = "completed" if outcome["success"] else "failed"
		episode.success = 1 if outcome["success"] else 0
		episode.utility = outcome.get("utility")
		episode.failure_type = outcome.get("failure_type")
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
			run_failure_type = outcome.get("failure_type")
			break  # spec section 13: a failed episode is a failure state, not silently skipped

	run.status = "cancelled" if cancelled else ("completed" if run_success else "failed")
	run.ended_at = now_datetime()
	if not run_success:
		run.failure_reason = run_failure_reason
		run.failure_type = run_failure_type
		run.retryable = 1 if run_failure_type in RETRYABLE_FAILURE_TYPES else 0
	telemetry = ctx.telemetry
	run.model_calls = telemetry["model_calls"]
	run.input_tokens = telemetry["input_tokens"]
	run.output_tokens = telemetry["output_tokens"]
	run.total_tokens = telemetry["total_tokens"] or (telemetry["input_tokens"] + telemetry["output_tokens"])
	run.retry_count = telemetry["retries"]
	run.wallclock_seconds = round(time.monotonic() - wallclock_started, 3)
	run.save(ignore_permissions=True)

	emit_event(
		ctx, "run_completed",
		payload={"status": run.status, "episodes_completed": len(episode_outcomes), "telemetry": dict(telemetry),
			"wallclock_seconds": run.wallclock_seconds},
	)
	run.event_count = frappe.db.count("EORL Event", {"run": run.name})
	run.save(ignore_permissions=True)

	return episode_outcomes


_ENDOGENOUS_SOURCES = (
	"chosen supplier or customer (decision-tool arguments)", "tool calls (tool_result events)",
	"messages (agent_message_* events)", "approvals (submit_* tools)", "ERP documents (erp_mutation events)",
	"memory (memory_write events)", "paths (derived from tool_result events)",
)


def _phase_for_episode(episode_number: int, regime_shift: Optional[dict]) -> str:
	if regime_shift and episode_number >= regime_shift.get("trigger_episode", float("inf")):
		return "shock"
	return "stable" if episode_number > 1 else "warmup"


def _regime_shift_payload(regime_shift: Optional[str]) -> Optional[dict]:
	if not regime_shift:
		return None
	shift_doc = frappe.get_doc("EORL Regime Shift", regime_shift)
	return {
		"name": shift_doc.name,
		"trigger_episode": shift_doc.trigger_episode,
		"parameter_delta_json": frappe.parse_json(shift_doc.parameter_delta_json or "{}"),
	}


def _scenario_snapshot(routine: dict, outcome_model: str) -> dict:
	return {
		"routine_template": routine["name"], "routine_version": routine.get("version"),
		"scenario_generator": routine["scenario_generator"], "outcome_model": outcome_model,
	}


def run_architecture(
	architecture_name: str,
	seed: int = 42,
	episode_count: int = 1,
	regime_shift: Optional[str] = None,
	actor_engine: Optional[str] = None,
	outcome_model: str = DEFAULT_OUTCOME_MODEL,
	experiment: Optional[str] = None,
	cell_id: Optional[str] = None,
	existing_run: Optional[str] = None,
	expected_denial_codes: Optional[list] = None,
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
	which architecture calls it.

	SOTA Milestone 1: also reads the architecture's bound
	`communication_policy` (if any) and threads it through so
	agent-chosen message_agent calls are checked against a real policy,
	not just the orchestrator's own structural handoffs.

	Submission-day additions:
	- the routine comes from the architecture's `routine_template`
	  (Procure-to-Pay when blank), so the same call runs any routine;
	- `actor_engine` overrides every actor's engine without changing the
	  architecture (eorl_lab.providers.factory.ACTOR_ENGINES);
	- `outcome_model` selects how exogenous outcomes are drawn (matched
	  across architectures by default; see eorl_lab.scenarios.procurement);
	- `experiment` and `cell_id` link the run to the design that produced it;
	- `existing_run` continues a run created earlier with status "queued"
	  (eorl_lab.api.queue)."""

	architecture = frappe.get_doc("EORL Architecture", architecture_name)
	slot_map = {row.slot_id: row.agent_template for row in architecture.actor_slots}
	routine = routines.resolve_routine(architecture.get("routine_template"))
	regime_shift_payload = _regime_shift_payload(regime_shift)
	engine_override = actor_engine if actor_engine and actor_engine != "as_configured" else None

	fields = {
		"run_seed": seed,
		"status": "running",
		"started_at": now_datetime(),
		"frappe_version": frappe.__version__,
		"architecture_snapshot_json": frappe.as_json(architecture.as_dict()),
		"agent_snapshots_json": frappe.as_json(_snapshot_agent_templates(slot_map)),
		"regime_shift_snapshot_json": frappe.as_json(regime_shift_payload) if regime_shift_payload else None,
		"scenario_snapshot_json": frappe.as_json(_scenario_snapshot(routine, outcome_model)),
		"routine_template": routine["name"],
		"actor_engine": engine_override or _configured_engine(slot_map),
		"experiment": experiment,
		"cell_id": cell_id,
		"code_commit": _code_commit(),
	}
	if existing_run:
		run = frappe.get_doc("EORL Run", existing_run)
		run.update(fields)
		run.save(ignore_permissions=True)
	else:
		run = frappe.get_doc({"doctype": "EORL Run", **fields}).insert(ignore_permissions=True)
		# A brand-new run cannot have been cancelled. A flag under its name
		# can only be left over from a rolled-back run that had the same name.
		frappe.cache().delete_value(f"eorl_cancel:{run.name}")

	ctx = ExperimentContext(run_id=run.name, experiment_id=experiment, cell_id=cell_id)
	ctx.engine_override = engine_override
	ctx.expected_denial_codes = tuple(expected_denial_codes or ())
	emit_event(
		ctx, "run_initialized",
		payload={
			"run": run.name, "seed": seed, "architecture": architecture.name,
			"coordination_mode": architecture.coordination_mode, "slot_map": slot_map,
			"episode_count": episode_count, "regime_shift": regime_shift,
			"communication_policy": architecture.communication_policy,
			"routine_template": routine["name"], "actor_engine": run.actor_engine,
			"outcome_model": outcome_model, "stage_gated_tools": bool(architecture.get("stage_gated_tools")),
			"experiment": experiment, "cell_id": cell_id,
		},
	)

	episode_outcomes = _run_episode_loop(
		ctx, run, slot_map, seed, episode_count, architecture.coordination_mode, regime_shift_payload,
		communication_policy=architecture.communication_policy, routine=routine, outcome_model=outcome_model,
		stage_gated=bool(architecture.get("stage_gated_tools")),
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


def _code_commit() -> str:
	from eorl_lab.observability.exporter import _app_repo_path, _git_commit

	return _git_commit(_app_repo_path("eorl_lab"))


def _configured_engine(slot_map: dict) -> str:
	"""The engine type the actors' own model profiles imply, or "mixed"."""
	engines = set()
	for template_name in slot_map.values():
		profile = frappe.db.get_value("EORL Agent Template", template_name, "model_profile")
		provider = frappe.db.get_value("EORL Model Profile", profile, "provider") if profile else None
		engines.add(engine_type_of(provider) if provider else "unknown")
	return engines.pop() if len(engines) == 1 else "mixed"


def run_queued(run_name: str, architecture_name: str, seed: int, episode_count: int, regime_shift: Optional[str] = None,
	actor_engine: Optional[str] = None, experiment: Optional[str] = None, cell_id: Optional[str] = None):
	"""Background-job entrypoint for eorl_lab.api.queue. A run cancelled
	while still queued is left as it is."""
	status = frappe.db.get_value("EORL Run", run_name, "status")
	if status != "queued" or _cancel_requested(run_name):
		if status == "queued":
			frappe.db.set_value("EORL Run", run_name, {"status": "cancelled", "ended_at": now_datetime()})
		return {"run": run_name, "skipped": True, "status": "cancelled" if status == "queued" else status}
	try:
		return run_architecture(
			architecture_name, seed=seed, episode_count=episode_count, regime_shift=regime_shift,
			actor_engine=actor_engine, experiment=experiment, cell_id=cell_id, existing_run=run_name,
		)
	except Exception as exc:
		frappe.db.rollback()
		frappe.db.set_value("EORL Run", run_name, {
			"status": "failed", "failure_reason": str(exc)[:1000], "failure_type": "infrastructure_error",
			"retryable": 1, "ended_at": now_datetime(),
		})
		frappe.db.commit()
		raise


def _clone_memory_through_branch_point(source_run_name: str, target_run_name: str, branch_episode: int) -> int:
	"""SOTA Milestone 2 (V2 section 17: clone actor memories at the
	branch point). Copies every EORL Memory Record written during the
	source run's episodes 1..branch_episode into the new target run, so
	the branch's actors start with the SAME accumulated memory the
	parent had at that point. The copied records still reference the
	ORIGINAL (parent-owned) episode documents -- episodes are never
	duplicated, only referenced -- consistent with
	get_full_branch_history()'s lineage-walk rather than data-copy
	approach to reconstructing pre-branch history."""
	episode_names = frappe.get_all(
		"EORL Episode",
		filters={"run": source_run_name, "episode_number": ["<=", branch_episode]},
		pluck="name",
	)
	if not episode_names:
		return 0

	records = frappe.get_all(
		"EORL Memory Record",
		filters={"run": source_run_name, "episode": ["in", episode_names]},
		fields=["episode", "actor", "domain", "case_summary", "action", "outcome", "success", "salience", "payload_json"],
	)
	for record in records:
		frappe.get_doc(
			{
				"doctype": "EORL Memory Record",
				"run": target_run_name,
				"episode": record.episode,
				"actor": record.actor,
				"domain": record.domain,
				"case_summary": record.case_summary,
				"action": record.action,
				"outcome": record.outcome,
				"success": record.success,
				"salience": record.salience,
				"payload_json": record.payload_json,
				"created_at": now_datetime(),
			}
		).insert(ignore_permissions=True)

	return len(records)


def get_full_branch_history(run_name: str) -> list:
	"""Reconstructs ONE continuous episode history for `run_name` by
	walking its parent_run/branch_point_episode lineage back to the
	root, then reading each ancestor's own episodes up to the point
	where the NEXT descendant diverged from it (spec section 17's
	requirement that "History_A[1:t] == History_B[1:t]" for two
	branches sharing a common ancestor through episode t). Pre-branch
	episodes are read from whichever run actually owns them -- never
	duplicated into `run_name`'s own episode list."""
	chain = [(run_name, None)]  # (run_name, episode_upper_bound); None = no cap (this run's own episodes)
	current = frappe.get_doc("EORL Run", run_name)
	while current.parent_run:
		chain.append((current.parent_run, current.branch_point_episode))
		current = frappe.get_doc("EORL Run", current.parent_run)
	chain.reverse()  # root first, run_name itself last

	history = []
	for ancestor_run, upper_bound in chain:
		episodes = frappe.get_all(
			"EORL Episode",
			filters={"run": ancestor_run},
			fields=["run", "name", "episode_number", "scenario_case_id", "phase", "success"],
			order_by="episode_number asc",
		)
		for ep in episodes:
			if upper_bound is not None and ep.episode_number > upper_bound:
				continue
			history.append(ep)
	return history


def branch_run(
	source_run_name: str,
	branch_episode: int,
	additional_episode_count: int = 1,
	architecture_name: Optional[str] = None,
	regime_shift: Optional[str] = None,
	intervention_description: str = "",
) -> dict:
	"""SOTA Milestone 2 (V2 section 17, the flagship counterfactual-
	branching capability). Clones actor memory accumulated through
	`branch_episode`, then launches a brand-new run that continues the
	SAME exogenous scenario stream (same seed) from episode
	branch_episode + 1 onward -- optionally under a DIFFERENT
	architecture or regime shift (the counterfactual intervention).
	Episodes 1..branch_episode are never duplicated or modified; they
	stay owned by the source run. Call get_full_branch_history() to
	reconstruct one continuous history across the branch point.

	Honest scope, stated plainly rather than overclaimed: ERP state
	itself is NOT cloned or forked. Every branch's post-branch-point
	tool calls create real, permanent ERPNext documents in the SAME
	shared company -- there is no per-branch isolated universe at the
	ERP layer (that would need per-branch site clones, V2 section 20's
	"scalable strategy", not built). Comparisons based on process/event
	data (paths, coherence, variety, actor continuity) are valid across
	branches since they derive purely from each branch's own events;
	comparisons that depend on absolute shared ERP aggregates (e.g.
	"current stock level") are NOT, since multiple branches mutate the
	same underlying ledger. See SOTA_ROADMAP.md."""

	source_run = frappe.get_doc("EORL Run", source_run_name)
	if (source_run.current_episode or 0) < branch_episode:
		frappe.throw(
			f"Cannot branch {source_run_name} at episode {branch_episode}: "
			f"it has only completed {source_run.current_episode or 0} episode(s)."
		)

	source_architecture_snapshot = frappe.parse_json(source_run.architecture_snapshot_json or "{}")
	target_architecture_name = architecture_name or source_architecture_snapshot.get("name")
	if not target_architecture_name:
		frappe.throw(
			f"Cannot branch {source_run_name}: no architecture_name given and the source run carries "
			"no architecture name in its own snapshot (it wasn't launched via run_architecture)."
		)

	architecture = frappe.get_doc("EORL Architecture", target_architecture_name)
	slot_map = {row.slot_id: row.agent_template for row in architecture.actor_slots}
	routine = routines.resolve_routine(architecture.get("routine_template"))
	regime_shift_payload = _regime_shift_payload(regime_shift)

	# A branch keeps the source run's outcome model and actor engine: the
	# intervention is the architecture or regime, nothing else.
	source_scenario = frappe.parse_json(source_run.scenario_snapshot_json or "{}")
	outcome_model = source_scenario.get("outcome_model") or "receipt_keyed_v1"
	engine_override = source_run.get("actor_engine") if source_run.get("actor_engine") in (
		"scripted_deterministic", "bounded_rational") else None

	branch_run_doc = frappe.get_doc(
		{
			"doctype": "EORL Run",
			"run_seed": source_run.run_seed,  # identical exogenous stream -- non-negotiable
			"status": "running",
			"started_at": now_datetime(),
			"frappe_version": frappe.__version__,
			"parent_run": source_run_name,
			"branch_point_episode": branch_episode,
			"architecture_snapshot_json": frappe.as_json(architecture.as_dict()),
			"agent_snapshots_json": frappe.as_json(_snapshot_agent_templates(slot_map)),
			"regime_shift_snapshot_json": frappe.as_json(regime_shift_payload) if regime_shift_payload else None,
			"scenario_snapshot_json": frappe.as_json(_scenario_snapshot(routine, outcome_model)),
			"routine_template": routine["name"],
			"actor_engine": engine_override or _configured_engine(slot_map),
			"experiment": source_run.get("experiment"),
		}
	).insert(ignore_permissions=True)

	ctx = ExperimentContext(run_id=branch_run_doc.name)
	ctx.engine_override = engine_override
	emit_event(
		ctx, "run_branched",
		payload={
			"parent_run": source_run_name,
			"branch_point_episode": branch_episode,
			"architecture": architecture.name,
			"intervention_description": intervention_description,
		},
	)
	emit_event(
		ctx, "run_initialized",
		payload={
			"run": branch_run_doc.name, "seed": source_run.run_seed, "architecture": architecture.name,
			"coordination_mode": architecture.coordination_mode, "slot_map": slot_map,
			"episode_count": additional_episode_count, "regime_shift": regime_shift,
			"communication_policy": architecture.communication_policy, "branched_from": source_run_name,
		},
	)

	cloned_memory_count = _clone_memory_through_branch_point(source_run_name, branch_run_doc.name, branch_episode)

	episode_outcomes = _run_episode_loop(
		ctx, branch_run_doc, slot_map, source_run.run_seed, additional_episode_count,
		architecture.coordination_mode, regime_shift_payload,
		communication_policy=architecture.communication_policy,
		start_episode=branch_episode + 1, routine=routine, outcome_model=outcome_model,
		stage_gated=bool(architecture.get("stage_gated_tools")),
	)

	frappe.get_doc(
		{
			"doctype": "EORL Branch",
			"parent_run": source_run_name,
			"source_episode": branch_episode,
			"child_run": branch_run_doc.name,
			"intervention_description": intervention_description,
			"created_at": now_datetime(),
		}
	).insert(ignore_permissions=True)

	last_outcome = episode_outcomes[-1] if episode_outcomes else {"success": False}
	return {
		"parent_run": source_run_name,
		"branch_run": branch_run_doc.name,
		"branch_point_episode": branch_episode,
		"architecture": architecture.name,
		"cloned_memory_count": cloned_memory_count,
		"episodes": episode_outcomes,
		"outcome": last_outcome,
		"event_count": branch_run_doc.event_count,
	}
