import frappe
from frappe.model.document import Document


class EORLEvent(Document):
	"""Append-only event log (spec section 6.12 / 16.4): once written, a
	record is never edited or deleted, by design, not just after a run
	completes."""

	def validate(self):
		if not self.is_new():
			frappe.throw("EORL Event records are append-only and cannot be modified after creation.")

	def on_trash(self):
		frappe.throw("EORL Event records are append-only and cannot be deleted.")
