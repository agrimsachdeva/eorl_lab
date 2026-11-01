import json

import frappe
from frappe.model.document import Document


def _csv(value):
	return [v.strip() for v in (value or "").split(",") if v.strip()]


class EORLRoutineTemplate(Document):
	def validate(self):
		stages = self._stages()
		if not stages:
			frappe.throw("stage_sequence_json must list at least one stage.")
		for i, stage in enumerate(stages):
			missing = [k for k in ("role", "slot", "tools", "completes_on") if not stage.get(k)]
			if missing:
				frappe.throw(f"Stage {i + 1} of {self.routine_name!r} is missing {missing}.")
		frappe.get_attr(self.scenario_generator)  # fails loudly on a bad path

	def _stages(self):
		try:
			return json.loads(self.stage_sequence_json or "[]")
		except ValueError:
			frappe.throw("stage_sequence_json is not valid JSON.")

	def to_definition(self) -> dict:
		"""The plain-dict form eorl_lab.routines.resolve_routine returns."""
		return {
			"description": self.description,
			"domain": self.domain,
			"version": self.version,
			"process_grammar": self.process_grammar,
			"scenario_generator": self.scenario_generator,
			"exogenous_state_function": self.exogenous_state_function,
			"memory_domain": self.memory_domain or self.domain or "default",
			"broad_slot": self.broad_slot,
			"broad_role": self.broad_role,
			"terminal_conditions": _csv(self.terminal_conditions),
			"outcome_keys": _csv(self.outcome_keys),
			"default_metrics": _csv(self.default_metrics),
			"stages": self._stages(),
		}
