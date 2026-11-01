import json

import frappe


def wizard():
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    args = {
        "language": "English",
        "country": "United States",
        "timezone": "America/Phoenix",
        "currency": "USD",
        "company_name": "Hoosier Ice Cream",
        "company_abbr": "HIC",
        "chart_of_accounts": "Standard",
        "domain": "Manufacturing",
        "fy_start_date": "2026-01-01",
        "fy_end_date": "2026-12-31",
        "full_name": "EORL Administrator",
    }
    print(json.dumps(setup_complete(args)))
    frappe.db.commit()
    print("companies:", frappe.get_all("Company", pluck="name"))
    print("warehouses:", frappe.get_all("Warehouse", filters={"company": "Hoosier Ice Cream"}, pluck="name"))


def master_data():
    for name in ("Bloomington Dairy", "Indiana Foods Inc"):
        if not frappe.db.exists("Supplier", name):
            frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": name,
                "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups",
                "supplier_type": "Company",
                "country": "United States",
            }).insert()
    if not frappe.db.exists("Item", "MILK-001"):
        frappe.get_doc({
            "doctype": "Item",
            "item_code": "MILK-001",
            "item_name": "Milk",
            "description": "Milk",
            "item_group": "Raw Material",
            "stock_uom": "Litre",
            "is_stock_item": 1,
            "is_purchase_item": 1,
            "include_item_in_manufacturing": 1,
            "standard_rate": 0.8,
            "item_defaults": [{
                "company": "Hoosier Ice Cream",
                "default_warehouse": "Stores - HIC",
                "expense_account": "Cost of Goods Sold - HIC",
                "buying_cost_center": "Main - HIC",
            }],
        }).insert()
    frappe.db.commit()
    print("suppliers:", frappe.get_all("Supplier", pluck="name"))
    print("item:", frappe.db.get_value("Item", "MILK-001", ["item_name", "item_group", "stock_uom"]))
