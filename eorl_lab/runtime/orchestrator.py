import frappe
from frappe.utils import now_datetime

from eorl_lab.erp.registry import get_tool
from eorl_lab.observability.context import ExperimentContext
from eorl_lab.observability.events import emit_event
from eorl_lab.providers.base import ModelRequest
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.runtime import authority
from eorl_lab.scenarios.procurement import generate_case

# Explicit step limit per actor turn (spec section 13: "no run should
# hang indefinitely"). The longest scripted turn (Accounts Payable: sense,
# invoice, submit invoice, pay, submit payment) needs 5; the ceiling is a
# safety bound, not the expected length.
MAX_STEPS_PER_ACTOR_TURN = 8

_RESULT_ID_KEYS = ("purchase_order", "purchase_receipt", "purchase_invoice", "payment_entry")


def _primary_result_id(result: dict):
	for key in _RESULT_ID_KEYS:
		if result.get(key):
			return result[key]
	return None


def _run_actor_turn(ctx: ExperimentContext, agent, provider, case: dict, handoff: dict) -> tuple[dict, bool, str]:
	"""Runs one persistent actor's turn: repeated decide -> authority
	check -> execute -> observe loop until the actor signals stop or the
	step cap is hit (loop/deadlock safety, spec section 13). Returns
	(scratch, success, failure_reason). `scratch` accumulates this actor's
	own tool results so later turns (and the next actor's handoff) can
	build on confirmed ERP state rather than agent narrative."""

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
	For this specialist/handoff architecture (spec section 2.3 Architecture
	A), the handoff topology is enforced by the orchestrator itself, not
	left to agent discretion -- that is what "explicit handoffs across
	process stages; limited cross-stage autonomy" means for Architecture
	A. Agent-initiated messaging becomes relevant for the broader-autonomy
	architecture (Architecture B), a later milestone."""
	emit_event(ctx, "agent_message_sent", actor_slot=from_role, target_type="agent", target_id=to_role, payload=content)
	emit_event(ctx, "agent_message_received", actor_slot=to_role, target_type="agent", target_id=from_role, payload=content)


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


# role name -> (agent_templates dict key, handoff builder from accumulated routine_state)
_SPECIALIST_SEQUENCE = [
	("Purchasing Agent", "purchasing_agent", lambda state: {}),
	("Purchasing Manager Agent", "purchasing_manager_agent", lambda state: {"purchase_order": state["purchase_order"]}),
	("Warehouse Agent", "warehouse_agent", lambda state: {"purchase_order": state["purchase_order"]}),
	("Accounts Payable Agent", "accounts_payable_agent", lambda state: {"purchase_receipt": state["purchase_receipt"]}),
]


def run_specialist_routine(agent_templates: dict, seed: int = 42) -> dict:
	"""Milestone 3: Architecture A (specialist/handoff, spec section 2.3).
	Four persistent actor slots -- Purchasing Agent, Purchasing Manager
	Agent, Warehouse Agent, Accounts Payable Agent -- each restricted to
	its own tools by its own EORL Tool Policy, hand off a full
	procure-to-pay routine (PO -> approval -> receipt -> invoice ->
	payment) with explicit, logged communication between stages.

	`agent_templates` maps role key -> EORL Agent Template name, e.g.
	{"purchasing_agent": "...", "purchasing_manager_agent": "...",
	 "warehouse_agent": "...", "accounts_payable_agent": "..."}
	"""

	run = frappe.get_doc(
		{
			"doctype": "EORL Run",
			"run_seed": seed,
			"status": "running",
			"started_at": now_datetime(),
			"frappe_version": frappe.__version__,
			"architecture_snapshot_json": frappe.as_json({"architecture": "specialist_handoff", "agents": agent_templates}),
		}
	).insert(ignore_permissions=True)

	ctx = ExperimentContext(run_id=run.name)
	emit_event(
		ctx, "run_initialized",
		payload={"run": run.name, "seed": seed, "architecture": "specialist_handoff", "agents": agent_templates},
	)

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
	routine_state: dict = {}
	outcome = {"success": False, "stage_results": {}}

	previous_role = None
	completed_all_stages = True

	for role_name, agent_key, handoff_fn in _SPECIALIST_SEQUENCE:
		agent_template_name = agent_templates[agent_key]
		agent = frappe.get_doc("EORL Agent Template", agent_template_name)

		try:
			handoff = handoff_fn(routine_state)
		except KeyError as exc:
			outcome["failure_reason"] = f"cannot hand off to {role_name}: missing {exc} from prior stage"
			completed_all_stages = False
			break

		if previous_role is not None:
			_handoff(ctx, previous_role, role_name, {"handoff": handoff})

		stage_scratch, stage_success, stage_failure_reason = _run_actor_turn(ctx, agent, provider, case, handoff)
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

	episode.status = "completed" if outcome["success"] else "failed"
	episode.success = 1 if outcome["success"] else 0
	episode.outcome_json = frappe.as_json(outcome)
	episode.ended_at = now_datetime()
	episode.save(ignore_permissions=True)

	emit_event(ctx, "episode_outcome", payload=outcome, success=outcome["success"])

	run.status = "completed" if outcome["success"] else "failed"
	run.ended_at = now_datetime()
	run.current_episode = 1
	if not outcome["success"]:
		run.failure_reason = outcome.get("failure_reason")
	run.save(ignore_permissions=True)

	emit_event(ctx, "run_completed", payload={"status": run.status})
	run.event_count = frappe.db.count("EORL Event", {"run": run.name})
	run.save(ignore_permissions=True)

	return {
		"run": run.name,
		"episode": episode.name,
		"outcome": outcome,
		"event_count": run.event_count,
	}
