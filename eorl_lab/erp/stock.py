import random

import frappe


def inspect_received_goods(purchase_receipt: str, _case: dict = None) -> dict:
	"""Ground-truth-driven quality inspection (V2 spec section 15): the
	REALIZED outcome is drawn from the scenario's own latent ground
	truth (the supplier's quality_probability), seeded deterministically
	by this specific receipt so the same seed always reproduces the same
	outcome -- but the agent only ever observes the result
	(quality_passed, units_rejected), never the underlying probability.
	V2's information-policy principle: agents don't see latent ground
	truth unless the information policy explicitly permits it, and
	nothing in this system does yet.

	`_case` is injected by the orchestrator (eorl_lab.runtime.orchestrator
	._call_tool_with_context) only for tools that declare this exact
	parameter name -- it is never part of an agent's own decision
	arguments, so an agent cannot forge or inspect it."""
	pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
	supplier = pr.supplier
	total_qty = sum(d.qty for d in pr.items)

	ground_truth = ((_case or {}).get("latent_ground_truth") or {}).get(supplier, {})
	quality_probability = ground_truth.get("quality_probability", 1.0)

	case_hash = (_case or {}).get("case_hash", "no-case")
	rng = random.Random(f"{case_hash}:{purchase_receipt}:quality_inspection")
	quality_passed = rng.random() < quality_probability
	units_rejected = 0 if quality_passed else max(1, round(total_qty * (1 - quality_probability)))

	return {
		"purchase_receipt": purchase_receipt,
		"supplier": supplier,
		"quality_passed": quality_passed,
		"units_rejected": units_rejected,
		"units_total": total_qty,
	}


def escalate_quality_exception(purchase_receipt: str, units_rejected: int) -> dict:
	"""Consequential action (EXCEPTION process stage): logs the quality
	exception directly onto the real ERPNext document's comment timeline
	-- a genuine, visible ERP action, not a side-channel note only this
	app can see."""
	pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
	pr.add_comment(
		"Comment",
		text=f"EORL quality exception: {units_rejected} unit(s) rejected on inspection.",
	)
	return {
		"purchase_receipt": purchase_receipt,
		"quality_exception_escalated": True,
		"units_rejected": units_rejected,
	}
