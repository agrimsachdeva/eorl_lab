from eorl_lab.memory.episodic import EpisodicMemoryStore


class RecentMemoryStore(EpisodicMemoryStore):
	"""Recent-k memory (spec section 14): pure recency, no outcome or
	similarity weighting. A thin, explicit specialization of the same
	storage/retrieval mechanics episodic memory uses, rather than a
	separate implementation that could silently drift from it."""

	def __init__(self):
		super().__init__(recency_weight=1.0, outcome_weight=0.0, similarity_weight=0.0)
