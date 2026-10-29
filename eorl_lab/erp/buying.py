import frappe
from frappe.utils import add_days, nowdate


def get_supplier_options(item_code: str, limit: int = 5) -> dict:
	"""Read/sensing tool (spec section 10). Lists item-specific suppliers
	when configured, otherwise falls back to any active Supplier so the
	tool is usable against the current master data."""
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


def create_purchase_order(
	*,
	supplier: str,
	item_code: str,
	qty: float,
	company: str,
	warehouse: str,
	rate: float = None,
	schedule_days: int = 7,
) -> dict:
	"""Consequential action (spec section 10). Creates -- but does not
	submit -- a real ERPNext Purchase Order. Submission is a separate,
	separately-authorized tool (submit_purchase_order), not implemented
	until a later milestone. Runs under the caller's normal ERPNext
	permissions (no ignore_permissions) so ERPNext roles stay a real
	defense-in-depth layer, per spec section 9."""
	if not frappe.db.exists("Supplier", supplier):
		frappe.throw(f"Unknown supplier: {supplier}")
	if not frappe.db.exists("Item", item_code):
		frappe.throw(f"Unknown item: {item_code}")

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
		"docstatus": po.docstatus,
		"grand_total": po.grand_total,
		"before_draft_count_for_supplier": before_count,
		"after_draft_count_for_supplier": after_count,
	}
