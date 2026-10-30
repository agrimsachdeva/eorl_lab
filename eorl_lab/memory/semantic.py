from typing import List, Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab.memory.base import MemoryStore


def _subject_key(action: str) -> str:
	"""Collapses a per-episode action summary (spec section 14's
	`action` field, e.g. "ordered_from:Indiana Foods Inc") into the
	stable SUBJECT a fact is actually about. "ordered_from:X" is about
	the supplier X; every other action verb today references a fresh,
	per-episode document name (a Purchase Order/Receipt/Payment Entry
	name is never the same twice), so there is no stable subject to
	generalize about beyond "I completed this stage" -- which is itself
	a legitimate, if boring, semantic fact (e.g. "approved: 12/12
	successful")."""
	if ":" in action:
		verb, obj = action.split(":", 1)
		if verb == "ordered_from":
			return f"supplier:{obj}"
		return verb
	return action or "unknown"


class SemanticMemoryStore(MemoryStore):
	"""Semantic memory (V2 section 14): consolidated, abstracted FACTS
	about the environment, not a growing log of raw episode traces
	(that is episodic/recent memory). Each distinct subject gets
	exactly ONE `EORL Memory Record` per (run, actor, domain); write()
	upserts it -- incrementing a running observation/success count and
	rewriting `action` into a consolidated statement -- instead of
	inserting a new row every episode. `salience` holds the running
	success rate, so retrieval favors well-established facts over
	single-observation ones."""

	def retrieve(self, *, run: str, actor: str, domain: Optional[str], k: int) -> List[dict]:
		filters = {"run": run, "actor": actor}
		if domain:
			filters["domain"] = domain
		records = frappe.get_all(
			"EORL Memory Record",
			filters=filters,
			fields=["name", "episode", "case_summary", "action", "outcome", "success", "salience", "payload_json"],
			order_by="salience desc, creation desc",
			limit_page_length=k,
		)
		return [dict(r) for r in records]

	def write(self, record: dict) -> dict:
		subject = _subject_key(record.get("action") or "")
		filters = {"run": record["run"], "actor": record["actor"], "domain": record.get("domain"), "case_summary": subject}
		existing_name = frappe.db.get_value("EORL Memory Record", filters, "name")
		observed_success = 1 if record.get("success") else 0
		latest_scratch = frappe.parse_json(record.get("payload_json") or "{}")

		if existing_name:
			doc = frappe.get_doc("EORL Memory Record", existing_name)
			payload = frappe.parse_json(doc.payload_json or "{}")
			observations = payload.get("observations", 1) + 1
			successes = payload.get("successes", 1 if doc.success else 0) + observed_success
			payload.update({"observations": observations, "successes": successes, "latest_scratch": latest_scratch})
			doc.action = f"{subject}: {successes}/{observations} successful observation(s)"
			doc.outcome = record.get("outcome")
			doc.success = 1 if successes > 0 else 0
			doc.salience = successes / observations
			doc.episode = record.get("episode")
			doc.payload_json = frappe.as_json(payload)
			doc.save(ignore_permissions=True)
			return doc.as_dict()

		new_record = dict(record)
		new_record["case_summary"] = subject
		new_record["action"] = f"{subject}: {observed_success}/1 successful observation(s)"
		new_record["salience"] = float(observed_success)
		new_record["payload_json"] = frappe.as_json({"observations": 1, "successes": observed_success, "latest_scratch": latest_scratch})
		new_record.setdefault("created_at", now_datetime())
		new_record["doctype"] = "EORL Memory Record"
		doc = frappe.get_doc(new_record).insert(ignore_permissions=True)
		return doc.as_dict()

	def reset(self, *, run: str, actor: str) -> None:
		for name in frappe.get_all("EORL Memory Record", filters={"run": run, "actor": actor}, pluck="name"):
			frappe.delete_doc("EORL Memory Record", name, ignore_permissions=True)
