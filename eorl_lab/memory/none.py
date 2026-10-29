from typing import List, Optional

from eorl_lab.memory.base import MemoryStore


class NoMemoryStore(MemoryStore):
	"""No memory (spec section 14): retrieval always empty, writes are
	silently discarded. Used when a profile has local_memory_enabled=0 or
	local_backend='none' -- an explicit experimental condition, not an
	error state."""

	def retrieve(self, *, run: str, actor: str, domain: Optional[str], k: int) -> List[dict]:
		return []

	def write(self, record: dict) -> dict:
		return {}
