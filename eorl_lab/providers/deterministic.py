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


def _choose_supplier(case, scratch, memory):
	"""Shared supplier-choice policy (spec section 14's routinization
	demonstration): used by both the specialist Purchasing Agent and the
	broad-autonomy General Purchasing Agent so the two architectures make
	the same kind of decision, differing only in organizational structure
	around it, not in the underlying decision rule itself (spec section
	2.3: "same external ground truth and objective task requirements")."""
	candidates = scratch["candidate_suppliers"] or []

	remembered_supplier = None
	for record in memory:  # already ranked most-relevant first by the memory store
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
	return supplier, basis, assessment


class DeterministicProvider(ModelProvider):
	"""Rule-based provider for tests and reproducible demos (spec section
	8.1). Milestone 2 scripted one role; Milestone 3 scripted one fixed
	policy per role in the specialist/handoff architecture (spec section
	2.3 Architecture A); Milestone 4 added memory-conditioned routinization
	for the Purchasing Agent. Milestone 5 adds the broad-autonomy policy
	(Architecture B): one actor performs every stage of the same routine
	with no handoffs, using the identical supplier-choice rule, so the two
	architectures are genuinely comparable rather than differing in what
	the "right" decision even is."""

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

		supplier, basis, assessment = _choose_supplier(case, scratch, memory)
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

	def _decide_general_purchasing_agent(self, context):
		"""Architecture B (broad autonomy, spec section 2.3): one actor
		walks the entire procure-to-pay chain itself. Same decision rules
		as the four specialists combined, but as one continuous actor
		with zero handoffs -- "fewer mandatory handoffs; greater actor
		continuity" by construction, not by a different policy."""
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

		if "purchase_order" not in scratch:
			supplier, basis, assessment = _choose_supplier(case, scratch, memory)
			return _decision(
				"create_purchase_order",
				{
					"supplier": supplier,
					"item_code": case["item_code"],
					"qty": case["qty"],
					"company": case["company"],
					"warehouse": case["warehouse"],
				},
				stop=False,
				basis=basis,
				assessment=assessment,
			)

		if "purchase_order_status" not in scratch:
			return _decision(
				"get_purchase_order",
				{"name": scratch["purchase_order"]},
				stop=False,
				basis="Deterministic policy: review the PO before approving it.",
				assessment="Reviewing own PO before approval (no handoff needed; same actor).",
			)

		if not scratch.get("purchase_order_submitted"):
			return _decision(
				"submit_purchase_order",
				{"name": scratch["purchase_order"]},
				stop=False,
				basis="Deterministic policy: approve a reviewed, in-policy PO.",
				assessment="Approving own PO.",
			)

		if "purchase_receipt" not in scratch:
			return _decision(
				"create_purchase_receipt",
				{"purchase_order": scratch["purchase_order"]},
				stop=False,
				basis="Deterministic policy: receive against the approved PO.",
				assessment="PO approved; recording receipt myself.",
			)

		if not scratch.get("purchase_receipt_submitted"):
			return _decision(
				"submit_purchase_receipt",
				{"name": scratch["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: finalize the recorded receipt.",
				assessment="Submitting own receipt.",
			)

		if "purchase_receipt_status" not in scratch:
			return _decision(
				"get_receipt_status",
				{"name": scratch["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: confirm the receipt before invoicing against it.",
				assessment="Confirming own submitted receipt before invoicing.",
			)

		if "purchase_invoice" not in scratch:
			return _decision(
				"create_purchase_invoice",
				{"purchase_receipt": scratch["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: invoice against the confirmed receipt.",
				assessment="Receipt confirmed; creating invoice myself.",
			)

		if not scratch.get("purchase_invoice_submitted"):
			return _decision(
				"submit_purchase_invoice",
				{"name": scratch["purchase_invoice"]},
				stop=False,
				basis="Deterministic policy: submit the invoice before paying it.",
				assessment="Submitting own invoice.",
			)

		if "payment_entry" not in scratch:
			return _decision(
				"create_payment_entry",
				{"purchase_invoice": scratch["purchase_invoice"]},
				stop=False,
				basis="Deterministic policy: pay the submitted invoice.",
				assessment="Invoice submitted; paying myself.",
			)

		return _decision(
			"submit_payment_entry",
			{"name": scratch["payment_entry"]},
			stop=True,
			basis="Deterministic policy: finalize payment.",
			assessment="Payment entry created; submitting to close the routine end to end.",
		)
