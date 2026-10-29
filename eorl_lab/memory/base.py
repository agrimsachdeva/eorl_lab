from abc import ABC, abstractmethod
from typing import List


class MemoryStore(ABC):
	"""Common interface (spec section 14). Memory is an experimental
	manipulation, not hidden convenience state: every retrieval and write
	goes through here so the orchestrator can log it (memory_query /
	memory_retrieval / memory_write events) regardless of backend."""

	@abstractmethod
	def retrieve(self, *, run: str, actor: str, domain: str, k: int) -> List[dict]:
		...

	@abstractmethod
	def write(self, record: dict) -> dict:
		...

	def snapshot(self, *, run: str, actor: str) -> List[dict]:
		return self.retrieve(run=run, actor=actor, domain=None, k=10_000)

	def reset(self, *, run: str, actor: str) -> None:
		raise NotImplementedError
