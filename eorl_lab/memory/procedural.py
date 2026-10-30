from typing import List, Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab.memory.base import MemoryStore


class ProceduralMemoryStore(MemoryStore):
	"""Procedural memory (V2 section 14): a single reinforced
	stimulus -> response HABIT per (run, actor, domain) -- how the actor
	tends to act, not a growing log of facts about the world (that is
	semantic memory) or raw episode traces (episodic/recent memory).
	Repeating the same successful action reinforces it (`salience`
	climbs toward 1.0, modeling habit strengthening); a genuinely
	different action resets the habit to a fresh, weak one (modeling
	habit extinction/replacement) rather than averaging the two
	together, since a habit is "what I currently do", not a blend of
	everything ever tried."""

	REINFORCEMENT_STEP = 0.1

	def retrieve(self, *, run: str, actor: str, domain: Optional[str], k: int) -> List[dict]:
		filters = {"run": run, "actor": actor}
		if domain:
			filters["domain"] = domain
		records = frappe.get_all(
			"EORL Memory Record",
			filters=filters,
			fields=["name", "episode", "case_summary", "action", "outcome", "success", "salience", "payload_json"],
			order_by="salience desc",
			limit_page_length=k,
		)
		return [dict(r) for r in records]

	def write(self, record: dict) -> dict:
		filters = {"run": record["run"], "actor": record["actor"], "domain": record.get("domain")}
		existing_name = frappe.db.get_value("EORL Memory Record", filters, "name")
		latest_scratch = frappe.parse_json(record.get("payload_json") or "{}")

		if existing_name:
			doc = frappe.get_doc("EORL Memory Record", existing_name)
			payload = frappe.parse_json(doc.payload_json or "{}")
			same_habit = doc.action == record.get("action") and record.get("success")
			if same_habit:
				strength = min(1.0, (doc.salience or 0.0) + self.REINFORCEMENT_STEP)
				repetitions = payload.get("repetitions", 1) + 1
			else:
				strength = self.REINFORCEMENT_STEP if record.get("success") else 0.0
				repetitions = 1
			payload.update({"repetitions": repetitions, "latest_scratch": latest_scratch})
			doc.action = record.get("action")
			doc.outcome = record.get("outcome")
			doc.success = 1 if record.get("success") else 0
			doc.salience = strength
			doc.episode = record.get("episode")
			doc.case_summary = record.get("case_summary")
			doc.payload_json = frappe.as_json(payload)
			doc.save(ignore_permissions=True)
			return doc.as_dict()

		new_record = dict(record)
		new_record["salience"] = self.REINFORCEMENT_STEP if record.get("success") else 0.0
		new_record["payload_json"] = frappe.as_json({"repetitions": 1, "latest_scratch": latest_scratch})
		new_record.setdefault("created_at", now_datetime())
		new_record["doctype"] = "EORL Memory Record"
		doc = frappe.get_doc(new_record).insert(ignore_permissions=True)
		return doc.as_dict()

	def reset(self, *, run: str, actor: str) -> None:
		for name in frappe.get_all("EORL Memory Record", filters={"run": run, "actor": actor}, pluck="name"):
			frappe.delete_doc("EORL Memory Record", name, ignore_permissions=True)
