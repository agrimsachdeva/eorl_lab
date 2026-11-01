"""Scenario generator for the second routine, order-to-cash
(submission-day plan section 2.1). Deliberately small: it exists to show
that the orchestrator, event store, metrics and Process Explorer are not
specific to procure-to-pay, not to support a study of its own.

Same contract as eorl_lab.scenarios.procurement.generate_case: a pure
function of (seed, episode, regime_shift), with the latent parameters
kept out of anything an actor sees.
"""
import copy
import hashlib
import json
from typing import Optional

from eorl_lab.scenarios.procurement import DEFAULT_OUTCOME_MODEL, _apply_ground_truth_override

CUSTOMERS = ["EORL Demo Customer", "EORL Second Customer"]

BASE_CASE = {
	"routine": "order_to_cash",
	# A non-stock sales item of its own, so the routine needs no stock and
	# leaves the procure-to-pay item untouched.
	"item_code": "EORL-O2C-TUB",
	"company": "Hoosier Ice Cream",
	"warehouse": "Stores - HIC",
	"selling_rate": 1.25,
	# Latent and never shown to an actor. Not yet read by any tool; it is
	# the hook for a collection-risk shock if this routine is ever used
	# in a study.
	"latent_ground_truth": {c: {"payment_reliability": 0.95} for c in CUSTOMERS},
}

QTY_BASE = 20
QTY_STEP = 5
QTY_CYCLE = 4


def generate_case(seed: int = 42, episode: int = 1, regime_shift: Optional[dict] = None, outcome_model: str = DEFAULT_OUTCOME_MODEL) -> dict:
	case = copy.deepcopy(BASE_CASE)
	case["case_id"] = f"O2C-{seed:04d}-{episode:04d}"
	case["episode"] = episode
	case["seed"] = seed
	case["customer"] = CUSTOMERS[(seed + episode) % len(CUSTOMERS)]
	case["qty"] = QTY_BASE + QTY_STEP * ((seed + episode) % QTY_CYCLE)
	if regime_shift:
		delta = regime_shift.get("parameter_delta_json") or regime_shift.get("parameter_delta") or {}
		post_shock = episode >= regime_shift.get("trigger_episode", float("inf"))
		_apply_ground_truth_override(case, delta.get("post_shock_latent_ground_truth" if post_shock else "pre_shock_latent_ground_truth"))
		if post_shock:
			case["qty"] = round(case["qty"] * delta.get("qty_multiplier", 1.0))
	case["case_hash"] = hashlib.sha256(json.dumps(case, sort_keys=True).encode("utf-8")).hexdigest()
	case["outcome_model"] = outcome_model
	return case


def exogenous_state(case: dict, regime_shift: Optional[dict] = None) -> dict:
	regime = "none"
	if regime_shift:
		regime = "post_shock" if case["episode"] >= regime_shift.get("trigger_episode", float("inf")) else "pre_shock"
	return {
		"qty": case["qty"], "customer": case["customer"], "selling_rate": case["selling_rate"],
		"latent_ground_truth": copy.deepcopy(case["latent_ground_truth"]), "regime": regime,
		"regime_shift": (regime_shift or {}).get("name"),
	}


def ensure_master_data(company: str = "Hoosier Ice Cream"):
	"""Creates the two demo customers and the sales item if they do not
	exist. Called when the Order-to-Cash routine template is seeded and by
	its tests."""
	import frappe

	if not frappe.db.exists("Item", BASE_CASE["item_code"]):
		frappe.get_doc({
			"doctype": "Item", "item_code": BASE_CASE["item_code"], "item_name": "EORL ice cream tub (order-to-cash demo)",
			"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups",
			"stock_uom": "Nos", "is_stock_item": 0, "is_sales_item": 1, "is_purchase_item": 0,
		}).insert(ignore_permissions=True)
	for name in CUSTOMERS:
		if not frappe.db.exists("Customer", name):
			frappe.get_doc({
				"doctype": "Customer", "customer_name": name, "customer_type": "Company",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups",
				"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
			}).insert(ignore_permissions=True)
