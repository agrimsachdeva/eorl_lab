from frappe.model.document import Document


class EORLExperiment(Document):
	"""Milestone 6 deviation from spec section 6.9: this supports exactly
	the one-factor, up-to-two-level design (architecture_a vs
	architecture_b) that Milestones 2-5 were built around, not a general
	N-factor factorial table with explicit cell definitions. Extending to
	arbitrary factors (model family, memory profile, etc. as additional
	levels) is future work for whoever builds the full Experiment Studio
	wizard; the cell-count/run-count arithmetic below generalizes
	trivially once that table exists."""

	def cell_count(self) -> int:
		return 2 if self.architecture_b else 1

	def total_run_count(self) -> int:
		return self.cell_count() * (self.repetitions_per_cell or 1)
