from eorl_lab.providers.base import ModelProvider, ModelRequest, ModelResponse


class DeterministicProvider(ModelProvider):
	"""Rule-based provider for tests and reproducible demos (spec section
	8.1). Encodes one fixed policy for the procure-to-pay vertical slice:
	sense supplier options first, then issue a purchase order against the
	first candidate supplier."""

	def generate(self, request: ModelRequest) -> ModelResponse:
		case = request.context.get("case", {})
		already_observed = request.context.get("already_observed_suppliers", False)

		if not already_observed:
			decision = {
				"decision_version": "1.0",
				"state_assessment": "No supplier options observed yet for this case.",
				"intended_action": "get_supplier_options",
				"tool_arguments": {"item_code": case.get("item_code")},
				"recipient": None,
				"confidence": 0.9,
				"decision_basis": "Deterministic policy: always sense before acting.",
				"stop": False,
			}
		else:
			candidates = case.get("candidate_suppliers") or []
			supplier = candidates[0] if candidates else None
			decision = {
				"decision_version": "1.0",
				"state_assessment": f"Observed {len(candidates)} candidate supplier(s).",
				"intended_action": "create_purchase_order",
				"tool_arguments": {
					"supplier": supplier,
					"item_code": case.get("item_code"),
					"qty": case.get("qty"),
					"company": case.get("company"),
					"warehouse": case.get("warehouse"),
				},
				"recipient": None,
				"confidence": 0.85,
				"decision_basis": "Deterministic policy: act on the first candidate supplier after sensing.",
				"stop": True,
			}

		return ModelResponse(decision=decision, provider="deterministic", resolved_model="deterministic-v1")
