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

	def __post_init__(self):
		if not self.correlation_id:
			self.correlation_id = self.trace_id

	def next_sequence(self) -> int:
		self.sequence_no += 1
		return self.sequence_no
