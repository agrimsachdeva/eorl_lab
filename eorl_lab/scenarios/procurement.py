import hashlib
import json

# Fixed against the real restored master data (Hoosier Ice Cream / MILK-001 /
# Bloomington Dairy, Indiana Foods Inc) so the Milestone 2 vertical slice is
# provable against this site today. The full seed-driven distributional
# generator (spec section 11 -- demand/lead-time/quality distributions,
# exception families, regime shifts) is deferred to the Scenario Studio
# milestone; this intentionally fixes ONE known-good case rather than
# approximating the generator early.
DEFAULT_CASE = {
	"case_id": "CASE-DEMO-0001",
	"item_code": "MILK-001",
	"qty": 600,
	"company": "Hoosier Ice Cream",
	"warehouse": "Stores - HIC",
	"candidate_suppliers": ["Bloomington Dairy", "Indiana Foods Inc"],
	"latent_ground_truth": {
		"Bloomington Dairy": {"delivery_probability": 0.95, "quality_probability": 0.89, "price": 0.82},
		"Indiana Foods Inc": {"delivery_probability": 0.78, "quality_probability": 0.98, "price": 0.80},
	},
	"exception": {"family": "none", "severity": 0.0},
}


def generate_case(seed: int = 42, episode: int = 1) -> dict:
	case = dict(DEFAULT_CASE)
	case["episode"] = episode
	case["seed"] = seed
	case_hash = hashlib.sha256(json.dumps(case, sort_keys=True).encode("utf-8")).hexdigest()
	case["case_hash"] = case_hash
	return case
