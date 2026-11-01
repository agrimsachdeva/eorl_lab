"""Semantic ERP tools for the order-to-cash routine (submission-day plan
section 2.1). Same conventions as eorl_lab.erp.buying: documents are
created through ERPNext's own mappers, run under the caller's normal
permissions, and are returned as small dicts of confirmed ERP state."""
import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from frappe.utils import add_days, nowdate


def get_customer_order(_case: dict = None) -> dict:
	"""Read/sensing tool: the incoming customer order request for this case."""
	case = _case or {}
	return {
		"customer": case.get("customer"), "item_code": case.get("item_code"), "qty": case.get("qty"),
		"company": case.get("company"), "warehouse": case.get("warehouse"),
	}


def create_sales_order(*, customer: str, item_code: str, qty: float, company: str, warehouse: str,
	rate: float = None, delivery_days: int = 3, _case: dict = None) -> dict:
	"""Consequential action: creates, but does not submit, a Sales Order.
	The selling rate comes from the scenario when the caller gives none."""
	if not frappe.db.exists("Customer", customer):
		frappe.throw(f"Unknown customer: {customer}")
	if rate is None and _case:
		rate = _case.get("selling_rate")
	so = frappe.get_doc({
		"doctype": "Sales Order", "customer": customer, "company": company,
		"transaction_date": nowdate(), "delivery_date": add_days(nowdate(), delivery_days),
		"items": [{"item_code": item_code, "qty": qty, "rate": rate or 0, "warehouse": warehouse,
			"delivery_date": add_days(nowdate(), delivery_days)}],
	})
	so.insert()
	return {"sales_order": so.name, "customer": so.customer, "docstatus": so.docstatus, "grand_total": so.grand_total}


def get_sales_order(name: str) -> dict:
	"""Read/sensing tool: confirm a Sales Order before fulfilling it."""
	if not frappe.db.exists("Sales Order", name):
		frappe.throw(f"Unknown Sales Order: {name}")
	so = frappe.get_doc("Sales Order", name)
	return {"sales_order": so.name, "sales_order_status": so.status, "docstatus": so.docstatus, "customer": so.customer}


def submit_sales_order(name: str) -> dict:
	"""Consequential action: confirms (submits) the Sales Order."""
	so = frappe.get_doc("Sales Order", name)
	so.submit()
	return {"sales_order": so.name, "sales_order_submitted": True, "docstatus": so.docstatus}


def create_delivery_note(sales_order: str) -> dict:
	"""Consequential action: ships against a submitted Sales Order."""
	dn = make_delivery_note(sales_order)
	dn.insert()
	return {"delivery_note": dn.name, "docstatus": dn.docstatus, "sales_order": sales_order}


def submit_delivery_note(name: str) -> dict:
	dn = frappe.get_doc("Delivery Note", name)
	dn.submit()
	return {"delivery_note": dn.name, "delivery_note_submitted": True, "docstatus": dn.docstatus}


def get_delivery_status(name: str) -> dict:
	"""Read/sensing tool: confirm the delivery before billing it."""
	if not frappe.db.exists("Delivery Note", name):
		frappe.throw(f"Unknown Delivery Note: {name}")
	dn = frappe.get_doc("Delivery Note", name)
	return {"delivery_note": dn.name, "delivery_note_status": dn.status, "docstatus": dn.docstatus}


def create_sales_invoice(delivery_note: str) -> dict:
	"""Consequential action: bills a submitted delivery."""
	si = make_sales_invoice(delivery_note)
	si.insert()
	return {"sales_invoice": si.name, "docstatus": si.docstatus, "delivery_note": delivery_note}


def submit_sales_invoice(name: str) -> dict:
	si = frappe.get_doc("Sales Invoice", name)
	si.submit()
	return {"sales_invoice": si.name, "sales_invoice_submitted": True, "docstatus": si.docstatus}


def create_customer_payment(sales_invoice: str) -> dict:
	"""Consequential action: records the customer's payment of a submitted
	invoice through ERPNext's own Invoice->Payment Entry mapper."""
	pe = get_payment_entry("Sales Invoice", sales_invoice)
	pe.reference_no = pe.reference_no or sales_invoice
	pe.reference_date = pe.reference_date or nowdate()
	pe.insert()
	return {"customer_payment": pe.name, "docstatus": pe.docstatus, "sales_invoice": sales_invoice}


def submit_customer_payment(name: str) -> dict:
	pe = frappe.get_doc("Payment Entry", name)
	pe.submit()
	return {"customer_payment": pe.name, "customer_payment_submitted": True, "docstatus": pe.docstatus}
