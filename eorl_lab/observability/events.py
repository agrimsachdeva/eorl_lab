import hashlib
from typing import Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab.observability.context import ExperimentContext


def emit_event(
	ctx: ExperimentContext,
	event_type: str,
	*,
	actor_slot: Optional[str] = None,
	actor_instance_id: Optional[str] = None,
	target_type: Optional[str] = None,
	target_id: Optional[str] = None,
	success: Optional[bool] = None,
	payload: Optional[dict] = None,
):
	"""Write one immutable EORL Event row. Uses ignore_permissions because
	this is the orchestrator's own bookkeeping, not an agent-authorized
	ERP mutation -- the authority firewall (eorl_lab.runtime.authority)
	is the gate for the latter, not this logger."""
	payload = payload or {}
	payload_json = frappe.as_json(payload)
	payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

	doc = frappe.get_doc(
		{
			"doctype": "EORL Event",
			"run": ctx.run_id,
			"episode": ctx.episode_id,
			"sequence_no": ctx.next_sequence(),
			"wallclock_timestamp": now_datetime(),
			"event_type": event_type,
			"actor_slot": actor_slot,
			"actor_instance_id": actor_instance_id,
			"trace_id": ctx.trace_id,
			"span_id": ctx.span_id,
			"parent_span_id": ctx.parent_span_id,
			"correlation_id": ctx.correlation_id,
			"target_type": target_type,
			"target_id": target_id,
			"success": 1 if success else (0 if success is False else None),
			"payload_json": payload_json,
			"payload_hash": payload_hash,
		}
	).insert(ignore_permissions=True)

	return doc
