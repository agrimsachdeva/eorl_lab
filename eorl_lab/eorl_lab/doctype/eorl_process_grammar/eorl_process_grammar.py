from frappe.model.document import Document


class EORLProcessGrammar(Document):
	def to_stage_map(self) -> dict:
		"""Derives a tool_name -> stage dict from this grammar's
		transitions (spec V2 section 5: "the process grammar should be
		queryable by the metrics engine"). Calling one of a transition's
		tools is interpreted as moving the process to that transition's
		to_stage. Returned as a plain dict so eorl_lab.analysis.paths
		stays a pure function of plain data (spec section 17's closing
		requirement) -- this method is the only place that touches
		Frappe; the resolved dict can be exported and reused outside it."""
		stage_map = {}
		for transition in self.transitions:
			for tool_name in (transition.tool_names or "").split(","):
				tool_name = tool_name.strip()
				if tool_name:
					stage_map[tool_name] = transition.to_stage
		return stage_map
