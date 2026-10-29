import frappe
from frappe.utils import now_datetime

from eorl_lab.erp.registry import get_tool
from eorl_lab.observability.context import ExperimentContext
from eorl_lab.observability.events import emit_event
from eorl_lab.providers.base import ModelRequest
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.runtime import authority
from eorl_lab.scenarios.procurement import generate_case

# Explicit step limit (spec section 13: "no run should hang indefinitely").
# Milestone 2's single deterministic case only ever needs 2 steps (sense,
# then act); the ceiling is a safety bound, not the expected length.
MAX_STEPS_PER_EPISODE = 6


def run_demo_episode(agent_template_name: str, seed: int = 42) -> dict:
	"""Milestone 2 vertical slice: one deterministic actor receives one
	procurement case, observes permitted ERP state, requests one semantic
	action, passes an authority check, creates a real ERPNext document,
	and produces a full event trace for one completed episode."""

	agent = frappe.get_doc("EORL Agent Template", agent_template_name)
	tool_policy = frappe.get_doc("EORL Tool Policy", agent.tool_policy)

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
	available_tools = [row.tool_name for row in tool_policy.allowed_semantic_tools]

	already_observed_suppliers = False
	write_count = 0
	outcome = {"success": False, "purchase_order": None}
	steps_taken = 0

	for step in range(MAX_STEPS_PER_EPISODE):
		steps_taken = step + 1

		request = ModelRequest(
			system_instructions=agent.initial_system_instructions or "",
			context={"case": case, "already_observed_suppliers": already_observed_suppliers},
			available_tools=available_tools,
		)

		emit_event(ctx, "agent_context_built", actor_slot=agent.organizational_role, payload={"step": step})
		emit_event(ctx, "model_request", actor_slot=agent.organizational_role, payload={"provider": "deterministic"})

		response = provider.generate(request)

		emit_event(
			ctx,
			"model_response",
			actor_slot=agent.organizational_role,
			payload={"provider": response.provider, "resolved_model": response.resolved_model},
		)

		decision = response.decision
		emit_event(ctx, "decision_parsed", actor_slot=agent.organizational_role, payload=decision)

		tool_name = decision["intended_action"]
		tool_args = decision.get("tool_arguments") or {}

		emit_event(
			ctx,
			"tool_requested",
			actor_slot=agent.organizational_role,
			target_type="tool",
			target_id=tool_name,
			payload=tool_args,
		)

		authority_decision = authority.evaluate(
			tool_policy_name=agent.tool_policy,
			tool_name=tool_name,
			tool_args={**tool_args, "_episode_write_count": write_count},
		)

		if not authority_decision.allowed:
			emit_event(
				ctx,
				"tool_denied",
				actor_slot=agent.organizational_role,
				target_type="tool",
				target_id=tool_name,
				success=False,
				payload=authority_decision.as_dict(),
			)
			outcome["failure_reason"] = authority_decision.reason_code
			break

		emit_event(
			ctx,
			"tool_authorized",
			actor_slot=agent.organizational_role,
			target_type="tool",
			target_id=tool_name,
			success=True,
			payload=authority_decision.as_dict(),
		)

		tool_fn = get_tool(tool_name)
		is_write = tool_name in authority.WRITE_TOOLS

		if is_write:
			emit_event(
				ctx,
				"erp_state_before",
				target_type="Purchase Order",
				payload={"supplier": tool_args.get("supplier"), "item_code": tool_args.get("item_code")},
			)

		try:
			result = tool_fn(**tool_args)
		except Exception as exc:
			# A failed tool call does not corrupt the trace already
			# recorded for this episode -- it becomes an observable
			# organizational-process failure, not a silent repair
			# (spec section 9 / 28).
			emit_event(
				ctx,
				"error",
				actor_slot=agent.organizational_role,
				target_type="tool",
				target_id=tool_name,
				success=False,
				payload={"error": str(exc)},
			)
			outcome["failure_reason"] = str(exc)
			break

		emit_event(
			ctx,
			"tool_result",
			actor_slot=agent.organizational_role,
			target_type="tool",
			target_id=tool_name,
			success=True,
			payload=result,
		)

		if tool_name in authority.READ_TOOLS:
			already_observed_suppliers = True

		if is_write:
			write_count += 1
			emit_event(
				ctx,
				"erp_mutation",
				target_type="Purchase Order",
				target_id=result.get("purchase_order"),
				success=True,
				payload=result,
			)
			emit_event(
				ctx,
				"erp_state_after",
				target_type="Purchase Order",
				target_id=result.get("purchase_order"),
				payload={"after_draft_count_for_supplier": result.get("after_draft_count_for_supplier")},
			)
			outcome["success"] = True
			outcome["purchase_order"] = result.get("purchase_order")

		if decision.get("stop"):
			break

	episode.status = "completed" if outcome["success"] else "failed"
	episode.success = 1 if outcome["success"] else 0
	episode.outcome_json = frappe.as_json(outcome)
	episode.cycle_steps = steps_taken
	episode.ended_at = now_datetime()
	episode.save(ignore_permissions=True)

	emit_event(ctx, "episode_outcome", payload=outcome, success=outcome["success"])

	run.status = "completed" if outcome["success"] else "failed"
	run.ended_at = now_datetime()
	run.current_episode = 1
	run.event_count = frappe.db.count("EORL Event", {"run": run.name})
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
