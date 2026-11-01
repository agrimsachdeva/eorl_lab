from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelRequest:
	system_instructions: str
	context: dict
	available_tools: list


@dataclass
class ModelResponse:
	decision: dict
	provider: str
	resolved_model: Optional[str] = None
	raw_text: Optional[str] = None
	token_counts: dict = field(default_factory=dict)
	latency_ms: Optional[float] = None
	provider_request_id: Optional[str] = None
	retry_count: int = 0


class ModelProvider(ABC):
	"""Common interface (spec section 8.1). The run loop must never
	hard-code a provider or model name; it only ever talks to this."""

	@abstractmethod
	def generate(self, request: ModelRequest) -> ModelResponse:
		...
