import itertools

from frappe.model.document import Document


class EORLExperiment(Document):
	"""Milestone 6 built exactly the one-factor, up-to-two-level design
	(architecture_a vs architecture_b) Milestones 2-5 were constructed
	around. SOTA Milestone 4 (V2 section 28.7) generalizes this to a real
	N-factor, K-level factorial design via the `factors` child table,
	WITHOUT changing architecture_a/architecture_b's existing behavior:
	when `factors` is empty, every method below falls back to the
	original 1-factor/2-level arithmetic byte-for-byte."""

	def _factor_groups(self) -> dict:
		groups = {}
		for row in self.factors:
			groups.setdefault(row.factor_name, []).append(row)
		return groups

	def cell_count(self) -> int:
		groups = self._factor_groups()
		if not groups:
			return 2 if self.architecture_b else 1
		count = 1
		for levels in groups.values():
			count *= len(levels)
		return count

	def total_run_count(self) -> int:
		return self.cell_count() * (self.repetitions_per_cell or 1)

	def factorial_cells(self) -> list:
		"""Cartesian product of every distinct factor_name's levels, as a
		list of {factor_name: EORL Experiment Factor row} dicts, one per
		cell. Empty list (not an error) when `factors` has no rows --
		callers fall back to the architecture_a/architecture_b path in
		that case, same as cell_count() does."""
		groups = self._factor_groups()
		if not groups:
			return []
		names = list(groups.keys())
		level_lists = [groups[name] for name in names]
		return [dict(zip(names, combo)) for combo in itertools.product(*level_lists)]
