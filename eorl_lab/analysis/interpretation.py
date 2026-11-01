"""Registered interpretation rules (submission-day plan section 20).

The pilot's interpretation rule was prose and had no case for the
outcome that occurred. Here a rule is structured data saved on the
Analysis Plan before launch, and this function maps every possible
combination of significance, direction and equivalence to one of four
labels. A test enumerates every combination to show none is missing.
"""
from typing import List, Optional

LABELS = ("consistent", "inconsistent", "inconclusive", "not_evaluated")
DIRECTIONS = ("a_greater", "b_greater", "nonzero")
COMBINATIONS = ("AND", "OR", "weighted", "separate")

DEFAULT_RULES = {
	"support_rule": "consistent",          # significant, in the predicted direction
	"contradiction_rule": "inconsistent",  # significant, opposite direction
	"equivalence_rule": "inconsistent",    # not significant, equivalence established (the rival's null holds)
	"inconclusive_rule": "inconclusive",   # not significant, equivalence not established or not tested
	"trivial_effect_rule": "inconclusive",  # significant but inside the equivalence bounds
}


def classify(*, expected_direction: str, p_value: Optional[float], mean_diff: Optional[float], alpha: float = 0.05,
	equivalent: Optional[bool] = None, rules: Optional[dict] = None) -> dict:
	"""One registered outcome. `mean_diff` is A minus B. `equivalent`
	is the TOST verdict, or None when no equivalence test was registered.
	Returns the label and the cell of the rule table that produced it."""
	rules = {**DEFAULT_RULES, **{k: v for k, v in (rules or {}).items() if v}}
	for key, value in rules.items():
		if value not in LABELS[:3]:
			raise ValueError(f"{key} must be one of {LABELS[:3]} (got {value!r})")
	if expected_direction not in DIRECTIONS:
		raise ValueError(f"expected_direction must be one of {DIRECTIONS} (got {expected_direction!r})")

	if p_value is None or mean_diff is None:
		return {"label": "not_evaluated", "cell": "no_result"}

	significant = p_value < alpha
	if significant and equivalent:
		return {"label": rules["trivial_effect_rule"], "cell": "significant_and_equivalent"}
	if significant:
		if expected_direction == "nonzero":
			return {"label": rules["support_rule"], "cell": "significant_predicted_direction"}
		predicted = (mean_diff > 0) if expected_direction == "a_greater" else (mean_diff < 0)
		if predicted:
			return {"label": rules["support_rule"], "cell": "significant_predicted_direction"}
		return {"label": rules["contradiction_rule"], "cell": "significant_opposite_direction"}
	if equivalent:
		return {"label": rules["equivalence_rule"], "cell": "not_significant_equivalent"}
	return {"label": rules["inconclusive_rule"], "cell": "not_significant_not_equivalent"}


def combine(labels: List[str], rule: str = "AND", weights: Optional[List[float]] = None) -> dict:
	"""Combines per-outcome labels under a registered rule.

	AND: consistent only if every outcome is consistent; inconsistent if
	any is inconsistent. OR: consistent if any is consistent;
	inconsistent only if all are. weighted: consistent = +1,
	inconsistent = -1, inconclusive = 0, weighted mean above 0.5 is
	consistent and below -0.5 inconsistent. separate: no combined label.
	A missing result on any outcome makes the combined label
	not_evaluated under AND, OR and weighted."""
	if rule not in COMBINATIONS:
		raise ValueError(f"combination rule must be one of {COMBINATIONS} (got {rule!r})")
	if rule == "separate":
		return {"rule": rule, "label": None, "labels": labels}
	if not labels or "not_evaluated" in labels:
		return {"rule": rule, "label": "not_evaluated", "labels": labels}
	if rule == "AND":
		if "inconsistent" in labels:
			label = "inconsistent"
		elif all(l == "consistent" for l in labels):
			label = "consistent"
		else:
			label = "inconclusive"
	elif rule == "OR":
		if "consistent" in labels:
			label = "consistent"
		elif all(l == "inconsistent" for l in labels):
			label = "inconsistent"
		else:
			label = "inconclusive"
	else:
		weights = weights or [1.0] * len(labels)
		score_of = {"consistent": 1.0, "inconsistent": -1.0, "inconclusive": 0.0}
		total = sum(weights)
		score = sum(w * score_of[l] for w, l in zip(weights, labels)) / total if total else 0.0
		label = "consistent" if score > 0.5 else ("inconsistent" if score < -0.5 else "inconclusive")
		return {"rule": rule, "label": label, "labels": labels, "score": score}
	return {"rule": rule, "label": label, "labels": labels}
