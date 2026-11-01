import frappe

from eorl_lab.routines import seed_routine_templates
from eorl_lab.scenarios.order_to_cash import BASE_CASE, ensure_master_data


def execute():
	seed_routine_templates()
	if frappe.db.exists("Company", BASE_CASE["company"]):
		ensure_master_data(BASE_CASE["company"])
	frappe.db.commit()
