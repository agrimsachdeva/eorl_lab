import hashlib
import json
from typing import Optional

# Fixed against the real restored master data (Hoosier Ice Cream / MILK-001 /
# Bloomington Dairy, Indiana Foods Inc, ...) so the vertical slice is provable
# against this site today. The full seed-driven distributional generator
# (spec section 11 -- demand/lead-time/quality distributions, exception
# families) is deferred to the Scenario Studio milestone.
BASE_CASE = {
	"item_code": "MILK-001",
	"company": "Hoosier Ice Cream",
	"warehouse": "Stores - HIC",
	"candidate_suppliers": ["Bloomington Dairy", "Indiana Foods Inc"],
	"latent_ground_truth": {
		"Bloomington Dairy": {"delivery_probability": 0.95, "quality_probability": 0.89, "price": 0.82},
		"Indiana Foods Inc": {"delivery_probability": 0.78, "quality_probability": 0.98, "price": 0.80},
	},
	"exception": {"family": "none", "severity": 0.0},
}

QTY_STEP = 50
QTY_BASE = 500
QTY_CYCLE = 6  # qty cycles through QTY_BASE + {0, 50, 100, 150, 200, 250}


def generate_case(seed: int = 42, episode: int = 1, regime_shift: Optional[dict] = None) -> dict:
	"""Deterministic given (seed, episode, regime_shift): same inputs
	always produce the same case, including its hash -- this is what
	makes paired seeds (spec section 18) and the regime shift (section
	2.4) both possible without agents ever being told anything changed.

	`regime_shift` is a plain dict shaped like EORL Regime Shift's own
	fields ({"trigger_episode": int, "parameter_delta_json": {...}}), not
	a Frappe document, so this stays a pure function callable from tests
	without a site. Milestone 5 deviation: the only parameter_delta key
	currently read is "qty_multiplier" (a demand shock, spec section
	11's demand_distribution concept) -- supplier-reliability-reversal
	and exception-family shifts arrive with the full Scenario Studio
	generator. The shift is never written into the returned case as a
	flag agents could see; it only changes the ordinary `qty` value they
	already receive every episode (hidden_from_agents, spec section 2.4)."""

	case = dict(BASE_CASE)
	case["case_id"] = f"CASE-{seed:04d}-{episode:04d}"
	case["episode"] = episode
	case["seed"] = seed

	qty_multiplier = 1.0
	if regime_shift and episode >= regime_shift.get("trigger_episode", float("inf")):
		delta = regime_shift.get("parameter_delta_json") or regime_shift.get("parameter_delta") or {}
		qty_multiplier = delta.get("qty_multiplier", 1.0)

	base_qty = QTY_BASE + QTY_STEP * ((seed + episode) % QTY_CYCLE)
	case["qty"] = round(base_qty * qty_multiplier)

	case_hash = hashlib.sha256(json.dumps(case, sort_keys=True).encode("utf-8")).hexdigest()
	case["case_hash"] = case_hash
	return case
