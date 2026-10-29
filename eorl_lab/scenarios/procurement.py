import hashlib
import json

# Fixed against the real restored master data (Hoosier Ice Cream / MILK-001 /
# Bloomington Dairy, Indiana Foods Inc, ...) so the vertical slice is provable
# against this site today. The full seed-driven distributional generator
# (spec section 11 -- demand/lead-time/quality distributions, exception
# families, regime shifts) is deferred to the Scenario Studio milestone.
# Milestone 4 deviation from a "full" generator: only quantity varies
# deterministically per episode (seed, episode) -> qty; item/company/
# warehouse/suppliers stay fixed to known-good master data so repeated
# episodes are provably reproducible without depending on unverified
# item-supplier links for items other than MILK-001. Exceptions/regime
# shifts arrive with the Scenario Studio + regime-shift milestone.
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


def generate_case(seed: int = 42, episode: int = 1) -> dict:
	"""Deterministic given (seed, episode): same inputs always produce the
	same case, including its hash, so paired-seed replication (spec
	section 18) is already possible even before the full generator
	exists."""
	case = dict(BASE_CASE)
	case["case_id"] = f"CASE-{seed:04d}-{episode:04d}"
	case["episode"] = episode
	case["seed"] = seed
	case["qty"] = QTY_BASE + QTY_STEP * ((seed + episode) % QTY_CYCLE)

	case_hash = hashlib.sha256(json.dumps(case, sort_keys=True).encode("utf-8")).hexdigest()
	case["case_hash"] = case_hash
	return case
