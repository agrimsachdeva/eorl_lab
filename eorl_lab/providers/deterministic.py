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
			# Since the submission-day build an actor that saw the
			# inspection appends ";quality:passed|failed" to its action.
			candidate = action.split("ordered_from:", 1)[1].split(";", 1)[0]
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


def _supplier_rate(case, supplier):
	"""The chosen supplier's ground-truth unit price, passed explicitly
	into create_purchase_order rather than left for ERPNext's own
	Item Price / last_purchase_rate fallback chain to resolve. That
	fallback is fragile and self-referential (last_purchase_rate is
	itself set FROM each submitted transaction's rate), so once any one
	transaction resolves to 0 it silently corrupts every later run on
	this shared site. Ground truth is the actual source of the price in
	this scenario, so read it directly."""
	ground_truth = (case.get("latent_ground_truth") or {}).get(supplier) or {}
	return ground_truth.get("price")


def _decide_receipt_quality_steps(scratch):
	"""SOTA Milestone 1 (V2 sections 13/15): shared by the specialist
	Warehouse Agent and the broad-autonomy General Purchasing Agent --
	inspect goods on receipt (ground-truth-driven, not scripted), and if
	the inspection fails, escalate the exception onto the ERP record AND
	notify Accounts Payable via agent-chosen communication, before
	finally submitting the receipt either way. Returns a decision dict
	for the next required step in this sub-sequence, or None once it's
	complete (caller should move on to submit_purchase_receipt).

	This is the first place in the system where two episodes can
	legitimately produce two DIFFERENT tool-call sequences -- not just
	different argument values -- because the inspection's outcome is
	drawn from the scenario's own latent ground truth (see
	eorl_lab.erp.stock.inspect_received_goods), not fixed by this
	policy."""
	purchase_receipt = scratch["purchase_receipt"]

	if "quality_passed" not in scratch:
		return _decision(
			"inspect_received_goods",
			{"purchase_receipt": purchase_receipt},
			stop=False,
			basis="Deterministic policy: inspect goods on receipt before closing it out "
			"(V2 section 15: the realized outcome is drawn from ground truth, not scripted).",
			assessment="Receipt recorded; inspecting quality before finalizing.",
		)

	if not scratch["quality_passed"] and "quality_exception_escalated" not in scratch:
		return _decision(
			"escalate_quality_exception",
			{"purchase_receipt": purchase_receipt, "units_rejected": scratch.get("units_rejected")},
			stop=False,
			basis="Deterministic policy: a failed inspection is an exception that must be "
			"escalated onto the ERP record before closing the receipt (EXCEPTION process stage).",
			assessment=f"Inspection failed: {scratch.get('units_rejected')} unit(s) rejected. Escalating.",
		)

	if not scratch["quality_passed"] and "delivered" not in scratch:
		return _decision(
			"message_agent",
			{
				"recipient_slot": "Accounts Payable Agent",
				"content": f"Quality exception on {purchase_receipt}: {scratch.get('units_rejected')} unit(s) rejected.",
			},
			stop=False,
			basis="Deterministic policy: notify Accounts Payable directly before they invoice "
			"against this receipt (agent-chosen communication, V2 section 9) -- in addition to, "
			"not instead of, the ERP-record escalation.",
			assessment="Escalated on the ERP record; now notifying Accounts Payable directly.",
		)

	return None


class DeterministicProvider(ModelProvider):
	"""Rule-based provider for tests and reproducible demos (spec section
	8.1). Milestone 2 scripted one role; Milestone 3 scripted one fixed
	policy per role in the specialist/handoff architecture (spec section
	2.3 Architecture A); Milestone 4 added memory-conditioned routinization
	for the Purchasing Agent; Milestone 5 added the broad-autonomy policy.
	SOTA Milestone 1 adds the first ground-truth-driven branch (quality
	inspection on receipt) shared by both architectures, so the same
	policy can legitimately take two different paths depending on the
	scenario's own latent ground truth, not on a scripted toggle."""

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

	# Two hooks the bounded-rational engine overrides. The scripted
	# baseline always performs every optional check and always applies the
	# shared supplier rule.
	def _choose_supplier(self, case, scratch, memory):
		return _choose_supplier(case, scratch, memory)

	def _wants_check(self, context, check_name: str) -> bool:
		return True

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

		supplier, basis, assessment = self._choose_supplier(case, scratch, memory)
		return _decision(
			"create_purchase_order",
			{
				"supplier": supplier,
				"item_code": case["item_code"],
				"qty": case["qty"],
				"company": case["company"],
				"warehouse": case["warehouse"],
				"rate": _supplier_rate(case, supplier),
			},
			stop=True,
			basis=basis,
			assessment=assessment,
		)

	def _decide_purchasing_manager_agent(self, context):
		handoff = context["handoff"]
		scratch = context["scratch"]

		if "purchase_order_status" not in scratch and self._wants_check(context, "review_purchase_order"):
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

		if "purchase_order_status" not in scratch and self._wants_check(context, "confirm_purchase_order"):
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

		quality_step = _decide_receipt_quality_steps(scratch)
		if quality_step:
			return quality_step

		return _decision(
			"submit_purchase_receipt",
			{"name": scratch["purchase_receipt"]},
			stop=True,
			basis="Deterministic policy: finalize the recorded receipt.",
			assessment="Receipt recorded" + ("" if scratch.get("quality_passed") else " with exception handled") + "; submitting.",
		)

	def _decide_accounts_payable_agent(self, context):
		handoff = context["handoff"]
		scratch = context["scratch"]

		if "purchase_receipt_status" not in scratch and self._wants_check(context, "confirm_receipt"):
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
			supplier, basis, assessment = self._choose_supplier(case, scratch, memory)
			return _decision(
				"create_purchase_order",
				{
					"supplier": supplier,
					"item_code": case["item_code"],
					"qty": case["qty"],
					"company": case["company"],
					"warehouse": case["warehouse"],
					"rate": _supplier_rate(case, supplier),
				},
				stop=False,
				basis=basis,
				assessment=assessment,
			)

		if "purchase_order_status" not in scratch and self._wants_check(context, "review_purchase_order"):
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

		quality_step = _decide_receipt_quality_steps(scratch)
		if quality_step:
			return quality_step

		if not scratch.get("purchase_receipt_submitted"):
			return _decision(
				"submit_purchase_receipt",
				{"name": scratch["purchase_receipt"]},
				stop=False,
				basis="Deterministic policy: finalize the recorded receipt.",
				assessment="Submitting own receipt" + ("" if scratch.get("quality_passed") else " with exception handled") + ".",
			)

		if "purchase_receipt_status" not in scratch and self._wants_check(context, "confirm_receipt"):
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

	# ------------------------------------------------------------------
	# Order-to-cash (submission-day plan section 2.1): three specialist
	# roles and one broad role, same conventions as procure-to-pay.
	# ------------------------------------------------------------------

	def _o2c_next(self, context, steps):
		"""Returns the decision for the first step in `steps` whose result
		key is not yet in scratch. Each step is (result_key, tool, args_fn,
		optional_check_name or None)."""
		scratch = context["scratch"]
		pending = [st for st in steps if st[0] not in scratch and (st[3] is None or self._wants_check(context, st[3]))]
		for i, (key, tool, args_fn, _check) in enumerate(pending):
			return _decision(
				tool, args_fn(context), stop=(i == len(pending) - 1),
				basis=f"Deterministic policy: {tool.replace('_', ' ')}.",
				assessment=f"Next step: {tool}.",
			)
		return _decision("finish_turn", {}, stop=True, basis="Nothing left for this role.", assessment="Done.")

	@staticmethod
	def _o2c_order_args(ctx):
		case, scratch = ctx["case"], ctx["scratch"]
		return {"customer": scratch.get("customer") or case["customer"], "item_code": case["item_code"], "qty": case["qty"],
			"company": case["company"], "warehouse": case["warehouse"], "rate": case.get("selling_rate")}

	def _sales_steps(self):
		return [
			("customer", "get_customer_order", lambda c: {}, None),
			("sales_order", "create_sales_order", self._o2c_order_args, None),
			("sales_order_submitted", "submit_sales_order", lambda c: {"name": c["scratch"]["sales_order"]}, None),
		]

	def _fulfillment_steps(self, source):
		return [
			("sales_order_status", "get_sales_order", lambda c: {"name": source(c)["sales_order"]}, "confirm_sales_order"),
			("delivery_note", "create_delivery_note", lambda c: {"sales_order": source(c)["sales_order"]}, None),
			("delivery_note_submitted", "submit_delivery_note", lambda c: {"name": c["scratch"]["delivery_note"]}, None),
		]

	def _billing_steps(self, source):
		return [
			("delivery_note_status", "get_delivery_status", lambda c: {"name": source(c)["delivery_note"]}, "confirm_delivery"),
			("sales_invoice", "create_sales_invoice", lambda c: {"delivery_note": source(c)["delivery_note"]}, None),
			("sales_invoice_submitted", "submit_sales_invoice", lambda c: {"name": c["scratch"]["sales_invoice"]}, None),
			("customer_payment", "create_customer_payment", lambda c: {"sales_invoice": c["scratch"]["sales_invoice"]}, None),
			("customer_payment_submitted", "submit_customer_payment", lambda c: {"name": c["scratch"]["customer_payment"]}, None),
		]

	def _decide_sales_agent(self, context):
		return self._o2c_next(context, self._sales_steps())

	def _decide_fulfillment_agent(self, context):
		return self._o2c_next(context, self._fulfillment_steps(lambda c: c["handoff"]))

	def _decide_billing_agent(self, context):
		return self._o2c_next(context, self._billing_steps(lambda c: c["handoff"]))

	def _decide_general_order_agent(self, context):
		own = lambda c: c["scratch"]  # noqa: E731 -- one actor reads its own results instead of a handoff
		return self._o2c_next(context, self._sales_steps() + self._fulfillment_steps(own) + self._billing_steps(own))
