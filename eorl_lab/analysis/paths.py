from dataclasses import dataclass
from typing import List, Optional

# Default/fallback mapping, used when no EORL Process Grammar stage map is
# supplied. SOTA Milestone 1 makes this configurable (spec V2 section 5:
# "the process grammar should be queryable by the metrics engine") via
# EORL Process Grammar.to_stage_map() -- but these functions stay pure
# (plain dicts/lists in, no Frappe access) regardless of which map is used,
# per spec section 17's closing requirement.
PROCESS_STAGE_BY_TOOL = {
	"get_supplier_options": "SUPPLIER_SEARCH",
	"create_purchase_order": "PURCHASE_ORDER",
	"get_purchase_order": "PURCHASE_ORDER",
	"submit_purchase_order": "APPROVAL",
	"create_purchase_receipt": "RECEIPT",
	"submit_purchase_receipt": "RECEIPT",
	"get_receipt_status": "RECEIPT",
	"inspect_received_goods": "RECEIPT",
	"escalate_quality_exception": "EXCEPTION",
	"message_agent": "EXCEPTION",  # only used for exception-driven messaging today; see SOTA_ROADMAP.md
	"create_purchase_invoice": "INVOICE",
	"submit_purchase_invoice": "INVOICE",
	"create_payment_entry": "PAYMENT",
	"submit_payment_entry": "PAYMENT",
}


@dataclass
class CanonicalActionEvent:
	"""Spec section 17.1's canonical action event:
	(run, episode, order, actor, organizational_function, process_stage,
	action_type, target, success, timestamp)."""

	run: Optional[str]
	episode: Optional[str]
	order: int
	actor: Optional[str]
	organizational_function: Optional[str]
	process_stage: str
	action_type: Optional[str]
	target: Optional[str]
	success: bool
	timestamp: Optional[str]


def extract_canonical_events(events: List[dict], stage_map: Optional[dict] = None) -> List[CanonicalActionEvent]:
	"""Derives canonical action events from raw tool_result events only
	(not tool_requested/authorized/denied, which are authority bookkeeping,
	not the completed action itself). Accepts plain dicts shaped like
	eorl_lab.api.exports.export_run_bundle's "events" list -- this
	function never queries Frappe, so it is recomputable outside Frappe
	from an exported bundle, per spec section 17's closing requirement.

	`stage_map` overrides the default tool->stage mapping (e.g. with
	EORL Process Grammar.to_stage_map()'s output) without this function
	itself needing to touch Frappe.

	`actor` uses actor_instance_id (the specific bound Agent Template)
	when present, falling back to actor_slot (the role name) -- our
	actor-instance identity today IS the template, per spec section 8.4.
	`organizational_function` is always actor_slot (the role name): in
	every architecture built so far, one role performs one function, so
	this is not yet a meaningful second axis distinct from `actor`."""
	active_map = stage_map if stage_map is not None else PROCESS_STAGE_BY_TOOL
	canonical = []
	order = 0
	for event in events:
		if event.get("event_type") != "tool_result":
			continue
		tool_name = event.get("target_id")
		order += 1
		canonical.append(
			CanonicalActionEvent(
				run=event.get("run"),
				episode=event.get("episode"),
				order=order,
				actor=event.get("actor_instance_id") or event.get("actor_slot"),
				organizational_function=event.get("actor_slot"),
				process_stage=active_map.get(tool_name, "UNMAPPED"),
				action_type=tool_name,
				target=event.get("target_id"),
				success=bool(event.get("success")),
				timestamp=event.get("wallclock_timestamp"),
			)
		)
	return canonical


def process_path(events: List[dict], stage_map: Optional[dict] = None) -> List[str]:
	"""The canonical path for one episode: an ordered list of
	"STAGE:action_type" tokens, derived from that episode's events. This
	is the unit every sequence/coherence/repertoire metric below compares
	across episodes."""
	return [f"{e.process_stage}:{e.action_type}" for e in extract_canonical_events(events, stage_map)]


def actor_sequence(events: List[dict]) -> List[str]:
	return [e.actor for e in extract_canonical_events(events) if e.actor]


def functional_sequence(events: List[dict]) -> List[str]:
	return [e.organizational_function for e in extract_canonical_events(events) if e.organizational_function]
