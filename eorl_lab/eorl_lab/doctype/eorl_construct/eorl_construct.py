import frappe
from frappe.model.document import Document


class EORLConstruct(Document):
	"""V2 section 20: "Create a reusable library connecting theory to
	implementation." resolve_measurement_function() makes that
	connection real and testable -- a Construct whose
	`measurement_function` field names a function that doesn't actually
	exist fails loudly here, rather than silently documenting a
	capability the system doesn't have (spec sections 9/28)."""

	def resolve_measurement_function(self):
		if not self.measurement_function:
			raise NotImplementedError(
				f"EORL Construct {self.name!r} has no measurement_function configured yet "
				f"(see its validity_notes for why)."
			)
		return frappe.get_attr(self.measurement_function)
