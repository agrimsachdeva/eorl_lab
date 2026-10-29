from eorl_lab.providers.base import ModelProvider, ModelRequest, ModelResponse


def _decision(action, args, *, stop, basis, confidence=0.85, assessment=""):
	return {
		"decision_version": "1.0",
		"state_assessment": assessment,
		"intended_action": action,
		"tool_arguments": args,
		"recipient": None,
		"confidence": confidence,
		"decision_basis": basis,
		"stop": stop,
	}


class DeterministicProvider(ModelProvider):
	"""Rule-based provider for tests and reproducible demos (spec section
	8.1). Milestone 2 scripted one role; Milestone 3 scripts one fixed
	policy per organizational role in the specialist/handoff architecture
	(spec section 2.3 Architecture A). Milestone 4 additionally lets the
	Purchasing Agent condition on its own retrieved memory (spec section
	14) -- a small, honest demonstration of routinization: once it has
	successfully ordered from a supplier, it repeats that choice in later
	episodes rather than re-deriving it from scratch every time. Each
	method reads only `case`, `handoff` (what the previous actor passed
	forward), `scratch` (this actor's own accumulated tool results this
	turn), and `memory` -- never global ground truth the role isn't
	entitled to (spec section 8.3)."""

	def generate(self, request: ModelRequest) -> ModelResponse:
		role = request.context.get("organizational_role")
		handler = getattr(self, f"_decide_{self._slug(role)}", None)
		if handler is None:
			raise ValueError(f"DeterministicProvider has no scripted policy for role: {role!r}")

		decision = handler(request.context)
		return ModelResponse(decision=decision, provider="deterministic", resolved_model="deterministic-v1")

	@staticmethod
	def _slug(role):
		return (role or "").strip().lower().replace(" ", "_")

	def _decide_purchasing_agent(self, context):
		case = context["case"]
		scratch = context["scratch"]
		memory = context.get("memory") or []

		if "candidate_suppliers" not in scratch:
			return _decision(
				"get_supplier_options",
				{"item_code": case["item_code"]},
				stop=False,
				basis="Deterministic policy: sense supplier options before acting.",
				assessment="No supplier options observed yet for this case.",
			)

		candidates = scratch["candidate_suppliers"] or []

		remembered_supplier = None
		for record in memory:  # memory is already ranked most-relevant first by the memory store
			action = record.get("action") or ""
			if record.get("success") and action.startswith("ordered_from:"):
				candidate = action.split("ordered_from:", 1)[1]
				if candidate in candidates:
					remembered_supplier = candidate
					break

		supplier = remembered_supplier or (candidates[0] if candidates else None)
		if remembered_supplier:
			basis = "Deterministic policy: repeat a remembered successful supplier choice (routinization)."
			assessment = f"Recalled a prior successful order from {remembered_supplier}; repeating it."
		else:
			basis = "Deterministic policy: act on the first candidate supplier after sensing (no usable memory yet)."
			assessment = f"Observed {len(candidates)} candidate supplier(s); no prior memory to draw on."

		return _decision(
			"create_purchase_order",
			{
				"supplier": supplier,
				"item_code": case["item_code"],
				"qty": case["qty"],
				"company": case["company"],
				"warehouse": case["warehouse"],
			},
			stop=True,
			basis=basis,
			assessment=assessment,
		)

	def _decide_purchasing_manager_agent(self, context):
		handoff = context["handoff"]
		scratch = context["scratch"]

		if "purchase_order_status" not in scratch:
			return _decision(
				"get_purchase_order",
				{"name": handoff["purchase_order"]},
				stop=False,
				basis="Deterministic policy: review the PO before approving it.",
				assessment="Reviewing handed-off purchase order before approval.",
			)

		return _decision(
			"submit_purchase_order",
			{"name": handoff["purchase_order"]},
			stop=True,
			basis="Deterministic policy: approve a reviewed, in-policy PO.",
			assessment=f"PO status observed as {scratch.get('purchase_order_status')}; approving.",
		)

	def _decide_warehouse_agent(self, context):
		handoff = context["handoff"]
		scratch = context["scratch"]

		if "purchase_order_status" not in scratch:
			return _decision(
				"get_purchase_order",
				{"name": handoff["purchase_order"]},
				stop=False,
				basis="Deterministic policy: confirm what to receive before receiving it.",
				assessment="Confirming approved PO before recording receipt.",
			)

		if "purchase_receipt" not in scratch:
			return _decision(
				"create_purchase_receipt",
				{"purchase_order": handoff["purchase_order"]},
				stop=False,
				basis="Deterministic policy: receive against the approved PO.",
				assessment="PO confirmed approved; recording receipt.",
			)

		return _decision(
			"submit_purchase_receipt",
			{"name": scratch["purchase_receipt"]},
			stop=True,
			basis="Deterministic policy: finalize the recorded receipt.",
			assessment="Receipt recorded; submitting.",
		)

	def _decide_accounts_payable_agent(self, context):
		handoff = context["handoff"]
		scratch = context["scratch"]

		if "purchase_receipt_status" not in scratch:
			return _decision(
				"get_receipt_status",
				{"name": handoff["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: confirm the receipt before invoicing against it.",
				assessment="Confirming submitted receipt before invoicing.",
			)

		if "purchase_invoice" not in scratch:
			return _decision(
				"create_purchase_invoice",
				{"purchase_receipt": handoff["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: invoice against the confirmed receipt.",
				assessment="Receipt confirmed; creating invoice.",
			)

		if not scratch.get("purchase_invoice_submitted"):
			return _decision(
				"submit_purchase_invoice",
				{"name": scratch["purchase_invoice"]},
				stop=False,
				basis="Deterministic policy: submit the invoice before paying it.",
				assessment="Invoice created; submitting.",
			)

		if "payment_entry" not in scratch:
			return _decision(
				"create_payment_entry",
				{"purchase_invoice": scratch["purchase_invoice"]},
				stop=False,
				basis="Deterministic policy: pay the submitted invoice.",
				assessment="Invoice submitted; creating payment entry.",
			)

		return _decision(
			"submit_payment_entry",
			{"name": scratch["payment_entry"]},
			stop=True,
			basis="Deterministic policy: finalize payment.",
			assessment="Payment entry created; submitting to close the routine.",
		)
