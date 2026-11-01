"""A non-generative, bounded-rational actor engine (submission-day plan
section 9).

The scripted engine always does the same thing, so it can only check
that the instrument works. A language model can do anything, so on its
own it cannot say whether an organizational pattern comes from the
structure or from the model's semantics. This engine sits between them:
it has no natural-language reasoning at all, but it chooses, explores,
learns from what it can see, and sometimes skips optional checks. If a
mechanism shows up under this engine, the structure is enough to
produce it.

Behavior, all seeded from the scenario case so it is reproducible and
matched across architectures:

- Supplier choice: an estimate of each supplier's quality from the
  actor's own recalled memory records, (passes + 1) / (observations + 2),
  0.5 for a supplier it has no record of. It picks the highest estimate
  (ties go to the first listed supplier) and with probability
  `exploration_rate` picks uniformly at random instead. An actor learns
  only from records that carry an inspection result, which it has only
  if it observed the inspection itself. The specialist Purchasing Agent
  never does, so under specialist handoff it gets no quality feedback.
  That is a property of the architecture, not of the engine.
- Recall is bounded by the memory profile's top-k window. With memory
  disabled the actor recalls nothing and never learns.
- Optional read-only checks (reviewing a PO, confirming a receipt) are
  performed with probability `check_probability`. The draw is keyed on
  the case and the check, not the actor, so the specialist and broad
  actors facing the same case make the same choice about the same check.
"""
import random

from eorl_lab.providers.base import ModelRequest, ModelResponse
from eorl_lab.providers.deterministic import DeterministicProvider

ENGINE_VERSION = "bounded_rational_v1"
DEFAULT_EXPLORATION_RATE = 0.1
DEFAULT_CHECK_PROBABILITY = 0.5


def quality_evidence(memory: list) -> dict:
	"""{supplier: [passes, observations]} from recalled memory records
	whose action carries an inspection result."""
	evidence = {}
	for record in memory or []:
		action = record.get("action") or ""
		if not action.startswith("ordered_from:") or ";quality:" not in action:
			continue
		supplier, _, quality = action[len("ordered_from:"):].partition(";quality:")
		tally = evidence.setdefault(supplier, [0, 0])
		tally[1] += 1
		if quality == "passed":
			tally[0] += 1
	return evidence


class BoundedRationalProvider(DeterministicProvider):
	def __init__(self, exploration_rate: float = DEFAULT_EXPLORATION_RATE, check_probability: float = DEFAULT_CHECK_PROBABILITY):
		self.exploration_rate = exploration_rate
		self.check_probability = check_probability

	def generate(self, request: ModelRequest) -> ModelResponse:
		response = super().generate(request)
		return ModelResponse(decision=response.decision, provider="bounded_rational", resolved_model=ENGINE_VERSION)

	@staticmethod
	def _rng(case: dict, purpose: str) -> random.Random:
		return random.Random(f"{case.get('case_id')}:{case.get('seed')}:{purpose}")

	def _wants_check(self, context, check_name: str) -> bool:
		return self._rng(context["case"], f"check:{check_name}").random() < self.check_probability

	def _choose_supplier(self, case, scratch, memory):
		candidates = scratch.get("candidate_suppliers") or []
		if not candidates:
			return None, "No candidate suppliers observed.", "No candidates."
		evidence = quality_evidence(memory)
		estimates = {s: (evidence.get(s, [0, 0])[0] + 1) / (evidence.get(s, [0, 0])[1] + 2) for s in candidates}

		rng = self._rng(case, "supplier_choice")
		if rng.random() < self.exploration_rate:
			supplier = rng.choice(candidates)
			basis = "Bounded-rational policy: exploration draw, supplier chosen at random."
		else:
			supplier = max(candidates, key=lambda s: (estimates[s], -candidates.index(s)))
			basis = "Bounded-rational policy: highest recalled quality estimate."
		assessment = "Quality estimates from recalled records: " + ", ".join(
			f"{s}={estimates[s]:.2f} (n={evidence.get(s, [0, 0])[1]})" for s in candidates
		)
		return supplier, basis, assessment
