import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExperimentContext:
	"""Carries identity/trace propagation for one run, per spec section 16.1.

	Milestone 2 deviation: experiment_id/cell_id are left optional because
	the EORL Experiment DocType does not exist yet (it arrives with the
	Experiment Studio milestone); every event already carries run/episode,
	trace, span, and correlation identity so nothing here needs to change
	shape later, only gain values.
	"""

	run_id: str
	experiment_id: Optional[str] = None
	cell_id: Optional[str] = None
	episode_id: Optional[str] = None
	actor_id: Optional[str] = None
	trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
	span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
	parent_span_id: Optional[str] = None
	correlation_id: Optional[str] = None
	sequence_no: int = 0
	# Submission-day additions. `telemetry` accumulates per-run model-call
	# counts, tokens, latency and retries (plan section 23).
	# `expected_denial_codes` lets a run declare which authority denials
	# are part of its design (plan section 25).
	telemetry: dict = field(default_factory=lambda: {
		"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "retries": 0, "latency_ms": 0.0,
	})
	expected_denial_codes: tuple = ()
	engine_override: Optional[str] = None

	def __post_init__(self):
		if not self.correlation_id:
			self.correlation_id = self.trace_id

	def next_sequence(self) -> int:
		self.sequence_no += 1
		return self.sequence_no
