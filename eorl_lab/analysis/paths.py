import json
from dataclasses import dataclass, field
from typing import List, Optional

from eorl_lab.analysis import taxonomy

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
	"finish_turn": "CONTROL",
	# Order-to-cash, the second routine (submission-day plan section 2.1).
	"get_customer_order": "ORDER_INTAKE",
	"create_sales_order": "SALES_ORDER",
	"get_sales_order": "SALES_ORDER",
	"submit_sales_order": "ORDER_APPROVAL",
	"create_delivery_note": "FULFILLMENT",
	"submit_delivery_note": "FULFILLMENT",
	"get_delivery_status": "BILLING",
	"create_sales_invoice": "BILLING",
	"submit_sales_invoice": "BILLING",
	"create_customer_payment": "COLLECTION",
	"submit_customer_payment": "COLLECTION",
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
	# Submission-day additions: the taxonomy category (sense, decide,
	# execute, ...) and the attribute vector used by attribute-level path
	# coherence (eorl_lab.analysis.attribute_coherence).
	category: str = "execute"
	attributes: dict = field(default_factory=dict)
	decision_value: Optional[str] = None


def _payload(event) -> dict:
	raw = event.get("payload_json")
	if not raw:
		return event.get("payload") or {}
	if isinstance(raw, dict):
		return raw
	try:
		return json.loads(raw)
	except (TypeError, ValueError):
		return {}


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
	this is not yet a meaningful second axis distinct from `actor`.

	Each event also carries an attribute vector. `supplier` and
	`exception_state` are episode context: once a purchase order names a
	supplier, or an inspection fails, every later action in the same
	episode carries that value. Both reset when the episode changes. When
	events carry no payload (older exports), those two attributes are
	None and coherence skips them."""
	active_map = stage_map if stage_map is not None else PROCESS_STAGE_BY_TOOL
	canonical = []
	order = 0
	current_episode = object()
	context = {}
	for event in events:
		if event.get("event_type") != "tool_result":
			continue
		if event.get("episode") != current_episode:
			current_episode = event.get("episode")
			context = {"supplier": None, "customer": None, "exception_state": "normal"}
		tool_name = event.get("target_id")
		payload = _payload(event)
		if payload.get("supplier"):
			context["supplier"] = payload["supplier"]
		if payload.get("customer"):
			context["customer"] = payload["customer"]
		if payload.get("quality_passed") is False:
			context["exception_state"] = "quality_exception"

		decision_key = taxonomy.DECISION_ATTRIBUTE_BY_TOOL.get(tool_name)
		decision_value = payload.get(decision_key) if decision_key else None

		order += 1
		stage = active_map.get(tool_name, "UNMAPPED")
		canonical.append(
			CanonicalActionEvent(
				run=event.get("run"),
				episode=event.get("episode"),
				order=order,
				actor=event.get("actor_instance_id") or event.get("actor_slot"),
				organizational_function=event.get("actor_slot"),
				process_stage=stage,
				action_type=tool_name,
				target=event.get("target_id"),
				success=bool(event.get("success")),
				timestamp=event.get("wallclock_timestamp"),
				category=taxonomy.category_for(tool_name),
				decision_value=decision_value,
				attributes={
					"actor": event.get("actor_instance_id") or event.get("actor_slot"),
					"role": event.get("actor_slot"),
					"stage": stage,
					"object_type": taxonomy.TOOL_OBJECT_TYPE.get(tool_name),
					"counterparty": context["supplier"] or context["customer"],
					"exception_state": context["exception_state"] if payload or event.get("payload_json") else None,
					"tool_family": taxonomy.category_for(tool_name),
					"decision_domain": taxonomy.TOOL_DECISION_DOMAIN.get(tool_name),
				},
			)
		)
	return canonical


def scoped_events(events: List[dict], scope: str = "all_actions", stage_map: Optional[dict] = None) -> List[CanonicalActionEvent]:
	"""Canonical events restricted to one registered sequence view
	(eorl_lab.analysis.taxonomy.SEQUENCE_SCOPES)."""
	return [e for e in extract_canonical_events(events, stage_map) if taxonomy.in_scope(e.action_type, scope)]


def _token(e: CanonicalActionEvent, scope: str) -> str:
	if scope == "actor_function_actions":
		return f"{e.organizational_function}:{e.action_type}"
	token = f"{e.process_stage}:{e.action_type}"
	if scope != "all_actions" and e.decision_value:
		token += f"[{e.decision_value}]"
	return token


def process_path(events: List[dict], stage_map: Optional[dict] = None, scope: str = "all_actions") -> List[str]:
	"""The canonical path for one episode: an ordered list of
	"STAGE:action_type" tokens, derived from that episode's events. This
	is the unit every sequence/coherence/repertoire metric below compares
	across episodes.

	`scope` selects a registered sequence view. `all_actions` (the
	default) is the Milestone 7 definition, unchanged. The other views
	drop non-consequential calls and annotate the decision-bearing token
	with its choice (create_purchase_order[Supplier]), so a change of
	supplier is a change of path. `actor_function_actions` tokens are
	"ROLE:action" rather than "STAGE:action"."""
	return [_token(e, scope) for e in scoped_events(events, scope, stage_map)]


def actor_sequence(events: List[dict]) -> List[str]:
	return [e.actor for e in extract_canonical_events(events) if e.actor]


def functional_sequence(events: List[dict]) -> List[str]:
	return [e.organizational_function for e in extract_canonical_events(events) if e.organizational_function]
