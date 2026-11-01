import copy
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

# How a realized exogenous outcome (today: the quality inspection) is
# drawn. "matched_v2" (submission-day plan section 21) keys the draw on
# the scenario case and the chosen supplier only, never on an ERP
# document name, so the same action under two architectures meets the
# same outcome. "receipt_keyed_v1" is the original draw, keyed on the
# receipt name; it is kept so runs recorded before the change still
# reproduce (eorl_lab.observability.replay).
OUTCOME_MODELS = ("matched_v2", "receipt_keyed_v1")
DEFAULT_OUTCOME_MODEL = "matched_v2"

QTY_STEP = 50
QTY_BASE = 500
QTY_CYCLE = 6  # qty cycles through QTY_BASE + {0, 50, 100, 150, 200, 250}


def generate_case(seed: int = 42, episode: int = 1, regime_shift: Optional[dict] = None, outcome_model: str = DEFAULT_OUTCOME_MODEL) -> dict:
	"""Deterministic given (seed, episode, regime_shift): same inputs
	always produce the same case, including its hash -- this is what
	makes paired seeds (spec section 18) and the regime shift (section
	2.4) both possible without agents ever being told anything changed.

	`regime_shift` is a plain dict shaped like EORL Regime Shift's own
	fields ({"trigger_episode": int, "parameter_delta_json": {...}}), not
	a Frappe document, so this stays a pure function callable from tests
	without a site. parameter_delta keys read: "qty_multiplier" (a demand
	shock, from the trigger on), and "pre_shock_latent_ground_truth" /
	"post_shock_latent_ground_truth" ({supplier: {field: value}}
	overrides of the latent supplier parameters, the supplier-quality
	reversal). The shift is never written into the returned case as a
	flag agents could see; it changes `qty`, which agents already
	receive, and latent values, which they never receive
	(hidden_from_agents, spec section 2.4)."""

	case = copy.deepcopy(BASE_CASE)
	case["case_id"] = f"CASE-{seed:04d}-{episode:04d}"
	case["episode"] = episode
	case["seed"] = seed

	qty_multiplier = 1.0
	if regime_shift:
		delta = regime_shift.get("parameter_delta_json") or regime_shift.get("parameter_delta") or {}
		post_shock = episode >= regime_shift.get("trigger_episode", float("inf"))
		# Supplier-quality reversal (submission-day plan section 5): the
		# regime declares the latent supplier parameters on both sides of
		# the trigger, so the pre-shock world is part of the registered
		# design rather than whatever BASE_CASE happens to hold.
		override_key = "post_shock_latent_ground_truth" if post_shock else "pre_shock_latent_ground_truth"
		_apply_ground_truth_override(case, delta.get(override_key))
		if post_shock:
			qty_multiplier = delta.get("qty_multiplier", 1.0)

	base_qty = QTY_BASE + QTY_STEP * ((seed + episode) % QTY_CYCLE)
	case["qty"] = round(base_qty * qty_multiplier)

	case_hash = hashlib.sha256(json.dumps(case, sort_keys=True).encode("utf-8")).hexdigest()
	case["case_hash"] = case_hash
	# Set after hashing so the hash of every case that existed before
	# outcome models were versioned is unchanged.
	case["outcome_model"] = outcome_model
	return case


def _apply_ground_truth_override(case: dict, override: Optional[dict]):
	for supplier, fields in (override or {}).items():
		case["latent_ground_truth"].setdefault(supplier, {}).update(fields)


def exogenous_state(case: dict, regime_shift: Optional[dict] = None) -> dict:
	"""The exogenous half of the episode state, logged on every
	environment_observed event. `regime` is "none", "pre_shock" or
	"post_shock"."""
	regime = "none"
	if regime_shift:
		regime = "post_shock" if case["episode"] >= regime_shift.get("trigger_episode", float("inf")) else "pre_shock"
	return {
		"qty": case["qty"],
		"candidate_suppliers": list(case.get("candidate_suppliers") or []),
		"latent_ground_truth": copy.deepcopy(case.get("latent_ground_truth") or {}),
		"regime": regime,
		"regime_shift": (regime_shift or {}).get("name"),
	}
