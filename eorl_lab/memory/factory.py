from eorl_lab.memory.base import MemoryStore
from eorl_lab.memory.episodic import EpisodicMemoryStore
from eorl_lab.memory.none import NoMemoryStore
from eorl_lab.memory.procedural import ProceduralMemoryStore
from eorl_lab.memory.recent import RecentMemoryStore
from eorl_lab.memory.semantic import SemanticMemoryStore

# "shared" (organizational memory shared across actors) and "vector"
# (embedding-based retrieval) are both named in the EORL Memory Profile
# schema since Milestone 1 but are out of scope until shared-memory
# architectures and an embedding-model profile exist (later milestones;
# spec section 14 explicitly calls vector "optional extension").
# SOTA Milestone 3 implements "semantic" and "procedural", the two P1
# backends V2 section 14 names alongside episodic -- "shared" and
# "vector" remain P2/deferred.
_UNIMPLEMENTED_BACKENDS = {"shared", "vector"}


def get_memory_store(memory_profile) -> MemoryStore:
	"""Resolve an EORL Memory Profile document (or None) into the backend
	it asks for. Returns NoMemoryStore for "no memory configured" rather
	than raising, since that is a legitimate experimental condition."""
	if memory_profile is None or not memory_profile.local_memory_enabled:
		return NoMemoryStore()

	backend = memory_profile.local_backend or "none"

	if backend == "none":
		return NoMemoryStore()
	if backend == "recent":
		return RecentMemoryStore()
	if backend == "episodic":
		return EpisodicMemoryStore(
			recency_weight=memory_profile.recency_weight or 0.6,
			outcome_weight=memory_profile.outcome_weight or 0.4,
			similarity_weight=memory_profile.similarity_weight or 0.0,
		)
	if backend == "semantic":
		return SemanticMemoryStore()
	if backend == "procedural":
		return ProceduralMemoryStore()
	if backend in _UNIMPLEMENTED_BACKENDS:
		raise NotImplementedError(
			f"EORL Memory Profile backend '{backend}' is not implemented yet "
			"(requires shared-memory architecture / embedding support from a later milestone)."
		)

	raise ValueError(f"Unknown memory backend: {backend!r}")
