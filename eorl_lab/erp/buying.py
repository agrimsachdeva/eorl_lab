import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice
from frappe.utils import add_days, nowdate


def get_supplier_options(item_code: str, limit: int = 5, _case: dict = None) -> dict:
	"""Read/sensing tool (spec section 10). The candidate suppliers are
	exogenous scenario state (submission-day plan section 22): when the
	case names them, the tool returns those that exist in ERPNext, in the
	case's order, so the latent parameters the scenario (and any regime
	shift) assigns to them are the ones that apply. Without a case it
	lists item-specific suppliers, falling back to any active Supplier."""
	scenario_candidates = [s for s in ((_case or {}).get("candidate_suppliers") or []) if frappe.db.exists("Supplier", s)]
	if scenario_candidates:
		return {"item_code": item_code, "candidate_suppliers": scenario_candidates[: int(limit)]}

	suppliers = frappe.get_all(
		"Item Supplier",
		filters={"parent": item_code},
		fields=["supplier"],
		limit_page_length=limit,
	)
	names = [row.supplier for row in suppliers]

	if not names:
		names = frappe.get_all(
			"Supplier",
			filters={"disabled": 0},
			limit_page_length=limit,
			pluck="name",
		)

	return {"item_code": item_code, "candidate_suppliers": names}


def get_purchase_order(name: str) -> dict:
	"""Read/sensing tool: the Purchasing Manager and Warehouse Agent sense
	the PO rather than blindly trusting the handoff message's claim about
	it (spec section 4: ERP state is authoritative, not agent narrative)."""
	if not frappe.db.exists("Purchase Order", name):
		frappe.throw(f"Unknown Purchase Order: {name}")
	po = frappe.get_doc("Purchase Order", name)
	return {
		"purchase_order": po.name,
		"purchase_order_status": po.status,
		"docstatus": po.docstatus,
		"supplier": po.supplier,
		"company": po.company,
		"grand_total": po.grand_total,
		"items": [{"item_code": d.item_code, "qty": d.qty, "warehouse": d.warehouse} for d in po.items],
	}


def get_receipt_status(name: str) -> dict:
	"""Read/sensing tool: the Accounts Payable Agent confirms the receipt
	was actually submitted before invoicing against it."""
	if not frappe.db.exists("Purchase Receipt", name):
		frappe.throw(f"Unknown Purchase Receipt: {name}")
	pr = frappe.get_doc("Purchase Receipt", name)
	return {
		"purchase_receipt": pr.name,
		"purchase_receipt_status": pr.status,
		"docstatus": pr.docstatus,
		"purchase_order": pr.items[0].purchase_order if pr.items else None,
		"grand_total": pr.grand_total,
	}


def create_purchase_order(
	*,
	supplier: str,
	item_code: str,
	qty: float,
	company: str,
	warehouse: str,
	rate: float = None,
	schedule_days: int = 7,
	_case: dict = None,
) -> dict:
	"""Consequential action (spec section 10). Creates -- but does not
	submit -- a real ERPNext Purchase Order. Runs under the caller's
	normal ERPNext permissions (no ignore_permissions), per section 9's
	defense-in-depth requirement.

	SOTA Milestone 3 fix: when the caller doesn't supply `rate` (a real
	agent -- scripted or model-driven -- has no legitimate way to know
	the supplier's price; it's hidden ground truth, V2 section 2.4, not
	something it could type in), this resolves it from the scenario's
	own `latent_ground_truth[supplier].price` via the `_case` the
	orchestrator injects (eorl_lab.runtime.orchestrator
	._call_tool_with_context), the same way a real supplier-quoted price
	would be looked up automatically rather than invented by the
	purchasing agent. Resolving it here, server-side, means no caller --
	today's scripted policy or any future provider -- can accidentally
	leave the item's `rate` at 0 and corrupt ERPNext's own
	last_purchase_rate fallback chain for every subsequent order on this
	site (see SOTA_ROADMAP.md for the incident this fixes)."""
	if not frappe.db.exists("Supplier", supplier):
		frappe.throw(f"Unknown supplier: {supplier}")
	if not frappe.db.exists("Item", item_code):
		frappe.throw(f"Unknown item: {item_code}")

	if rate is None and _case:
		rate = (_case.get("latent_ground_truth") or {}).get(supplier, {}).get("price")

	before_count = frappe.db.count("Purchase Order", {"supplier": supplier, "docstatus": 0})

	schedule_date = add_days(nowdate(), schedule_days)
	po = frappe.get_doc(
		{
			"doctype": "Purchase Order",
			"supplier": supplier,
			"company": company,
			"schedule_date": schedule_date,
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate or 0,
					"warehouse": warehouse,
					"schedule_date": schedule_date,
				}
			],
		}
	).insert()

	after_count = frappe.db.count("Purchase Order", {"supplier": supplier, "docstatus": 0})

	return {
		"purchase_order": po.name,
		"supplier": po.supplier,
		"docstatus": po.docstatus,
		"grand_total": po.grand_total,
		"before_draft_count_for_supplier": before_count,
		"after_draft_count_for_supplier": after_count,
	}


def submit_purchase_order(name: str) -> dict:
	"""Consequential action: the Purchasing Manager Agent's approval step.
	A real ERPNext docstatus transition (draft -> submitted), not a
	cosmetic flag -- if the document fails ERPNext's own validation, this
	call fails loudly rather than being silently repaired (spec section 28)."""
	po = frappe.get_doc("Purchase Order", name)
	po.submit()
	return {"purchase_order": po.name, "purchase_order_submitted": True, "docstatus": po.docstatus}


def create_purchase_receipt(purchase_order: str) -> dict:
	"""Consequential action: the Warehouse Agent records goods received
	against a submitted PO, via ERPNext's own PO->Receipt mapper so taxes,
	UOM conversion, and account defaults are resolved the same way a human
	user's 'Make > Purchase Receipt' button would resolve them."""
	pr = make_purchase_receipt(purchase_order)
	pr.insert()
	return {"purchase_receipt": pr.name, "docstatus": pr.docstatus, "purchase_order": purchase_order}


def submit_purchase_receipt(name: str) -> dict:
	pr = frappe.get_doc("Purchase Receipt", name)
	pr.submit()
	return {"purchase_receipt": pr.name, "purchase_receipt_submitted": True, "docstatus": pr.docstatus}


def create_purchase_invoice(purchase_receipt: str) -> dict:
	"""Consequential action: the Accounts Payable Agent invoices against a
	submitted receipt (not the raw PO), via ERPNext's Receipt->Invoice
	mapper, matching the three-way PO/Receipt/Invoice relationship real
	accounts-payable processing depends on."""
	pi = make_purchase_invoice(purchase_receipt)
	pi.insert()
	return {"purchase_invoice": pi.name, "docstatus": pi.docstatus, "purchase_receipt": purchase_receipt}


def submit_purchase_invoice(name: str) -> dict:
	pi = frappe.get_doc("Purchase Invoice", name)
	pi.submit()
	return {"purchase_invoice": pi.name, "purchase_invoice_submitted": True, "docstatus": pi.docstatus}


def create_payment_entry(purchase_invoice: str) -> dict:
	"""Consequential action: pays a submitted invoice via ERPNext's own
	Invoice->Payment Entry mapper (resolves bank/cash account, exchange
	rate, and outstanding amount the same way the ERPNext UI would)."""
	pe = get_payment_entry("Purchase Invoice", purchase_invoice)
	pe.insert()
	return {"payment_entry": pe.name, "docstatus": pe.docstatus, "purchase_invoice": purchase_invoice}


def submit_payment_entry(name: str) -> dict:
	pe = frappe.get_doc("Payment Entry", name)
	pe.submit()
	return {"payment_entry": pe.name, "payment_entry_submitted": True, "docstatus": pe.docstatus}
