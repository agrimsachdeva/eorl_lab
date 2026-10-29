from typing import List, Optional

import frappe
from frappe.utils import now_datetime

from eorl_lab.memory.base import MemoryStore


class EpisodicMemoryStore(MemoryStore):
	"""Local episodic memory (spec section 14): every write/retrieval is a
	real `EORL Memory Record` row, scoped to one (run, actor) pair so
	actor memory never leaks across runs or across actors within a run.
	Retrieval ranks candidates by a weighted blend of recency and outcome
	(the EORL Memory Profile's recency_weight / outcome_weight fields,
	unused since Milestone 1 until now) -- similarity_weight is accepted
	but not yet meaningful without the vector backend (a later milestone)."""

	def __init__(self, recency_weight: float = 0.6, outcome_weight: float = 0.4, similarity_weight: float = 0.0):
		self.recency_weight = recency_weight or 0.0
		self.outcome_weight = outcome_weight or 0.0
		self.similarity_weight = similarity_weight or 0.0

	def retrieve(self, *, run: str, actor: str, domain: Optional[str], k: int) -> List[dict]:
		filters = {"run": run, "actor": actor}
		if domain:
			filters["domain"] = domain

		records = frappe.get_all(
			"EORL Memory Record",
			filters=filters,
			fields=["name", "episode", "case_summary", "action", "outcome", "success", "salience", "creation"],
			order_by="creation desc",
			limit_page_length=max(k * 4, 20),  # over-fetch a recency window, then re-rank below
		)

		n = len(records)
		scored = []
		for rank, record in enumerate(records):  # rank 0 = most recent
			recency_score = 1.0 - (rank / n) if n > 1 else 1.0
			outcome_score = 1.0 if record.success else 0.0
			score = self.recency_weight * recency_score + self.outcome_weight * outcome_score
			scored.append((score, record))

		scored.sort(key=lambda pair: pair[0], reverse=True)
		return [dict(record) for _score, record in scored[:k]]

	def write(self, record: dict) -> dict:
		record = dict(record)
		record.setdefault("created_at", now_datetime())
		record.setdefault("doctype", "EORL Memory Record")
		doc = frappe.get_doc(record).insert(ignore_permissions=True)
		return doc.as_dict()

	def reset(self, *, run: str, actor: str) -> None:
		for name in frappe.get_all("EORL Memory Record", filters={"run": run, "actor": actor}, pluck="name"):
			frappe.delete_doc("EORL Memory Record", name, ignore_permissions=True)
