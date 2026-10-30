import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.memory.procedural import ProceduralMemoryStore
from eorl_lab.memory.semantic import SemanticMemoryStore


class TestEORLSemanticMemory(FrappeTestCase):
	"""SOTA Milestone 3 (V2 section 14): semantic memory consolidates
	repeated observations about a stable SUBJECT into one fact, rather
	than growing one row per episode the way episodic/recent memory
	does."""

	def setUp(self):
		self.run = frappe.get_doc(
			{"doctype": "EORL Run", "run_seed": 1, "status": "running", "frappe_version": frappe.__version__}
		).insert(ignore_permissions=True)
		self.actor = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Semantic Memory Actor",
				"organizational_role": "Purchasing Agent",
				"model_profile": frappe.get_doc(
					{"doctype": "EORL Model Profile", "profile_name": "Test Semantic Memory Model Profile", "provider": "deterministic"}
				).insert(ignore_if_duplicate=True).name,
				"tool_policy": frappe.get_doc(
					{"doctype": "EORL Tool Policy", "policy_name": "Test Semantic Memory Tool Policy"}
				).insert(ignore_if_duplicate=True).name,
			}
		).insert(ignore_if_duplicate=True)
		self.store = SemanticMemoryStore()

	def _write(self, action, success):
		return self.store.write(
			{
				"run": self.run.name,
				"episode": None,
				"actor": self.actor.name,
				"domain": "procurement",
				"case_summary": "CASE-IRRELEVANT",  # episode-unique; semantic memory must not key on this
				"action": action,
				"outcome": "success" if success else "failure",
				"success": 1 if success else 0,
				"salience": 1.0,
				"payload_json": frappe.as_json({"supplier": "Indiana Foods Inc"}),
			}
		)

	def test_repeated_observations_of_the_same_subject_consolidate_into_one_fact(self):
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Indiana Foods Inc", False)

		records = frappe.get_all(
			"EORL Memory Record",
			filters={"run": self.run.name, "actor": self.actor.name, "case_summary": "supplier:Indiana Foods Inc"},
			fields=["name", "salience", "payload_json"],
		)
		self.assertEqual(len(records), 1, "three observations of the same subject must consolidate into one record")
		payload = frappe.parse_json(records[0].payload_json)
		self.assertEqual(payload["observations"], 3)
		self.assertEqual(payload["successes"], 2)
		self.assertAlmostEqual(records[0].salience, 2 / 3)

	def test_different_subjects_remain_distinct_facts(self):
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Bloomington Dairy", True)

		count = frappe.db.count("EORL Memory Record", {"run": self.run.name, "actor": self.actor.name})
		self.assertEqual(count, 2)

	def test_retrieve_ranks_by_salience_descending(self):
		self._write("ordered_from:Indiana Foods Inc", False)  # salience 0.0
		self._write("ordered_from:Bloomington Dairy", True)  # salience 1.0

		retrieved = self.store.retrieve(run=self.run.name, actor=self.actor.name, domain="procurement", k=2)
		self.assertEqual(len(retrieved), 2)
		self.assertEqual(retrieved[0]["case_summary"], "supplier:Bloomington Dairy")


class TestEORLProceduralMemory(FrappeTestCase):
	"""SOTA Milestone 3 (V2 section 14): procedural memory holds a single
	reinforced habit per (run, actor, domain) -- repeating the same
	successful action strengthens it; a different action resets it,
	rather than blending the two."""

	def setUp(self):
		self.run = frappe.get_doc(
			{"doctype": "EORL Run", "run_seed": 2, "status": "running", "frappe_version": frappe.__version__}
		).insert(ignore_permissions=True)
		self.actor = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Procedural Memory Actor",
				"organizational_role": "Purchasing Agent",
				"model_profile": frappe.get_doc(
					{"doctype": "EORL Model Profile", "profile_name": "Test Procedural Memory Model Profile", "provider": "deterministic"}
				).insert(ignore_if_duplicate=True).name,
				"tool_policy": frappe.get_doc(
					{"doctype": "EORL Tool Policy", "policy_name": "Test Procedural Memory Tool Policy"}
				).insert(ignore_if_duplicate=True).name,
			}
		).insert(ignore_if_duplicate=True)
		self.store = ProceduralMemoryStore()

	def _write(self, action, success):
		return self.store.write(
			{
				"run": self.run.name,
				"episode": None,
				"actor": self.actor.name,
				"domain": "procurement",
				"case_summary": "CASE-X",
				"action": action,
				"outcome": "success" if success else "failure",
				"success": 1 if success else 0,
				"salience": 1.0,
				"payload_json": "{}",
			}
		)

	def test_repeating_the_same_successful_action_strengthens_the_habit(self):
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Indiana Foods Inc", True)

		self.assertEqual(frappe.db.count("EORL Memory Record", {"run": self.run.name, "actor": self.actor.name}), 1)
		record = frappe.get_all(
			"EORL Memory Record", filters={"run": self.run.name, "actor": self.actor.name},
			fields=["salience", "payload_json"],
		)[0]
		self.assertAlmostEqual(record.salience, 0.3)
		self.assertEqual(frappe.parse_json(record.payload_json)["repetitions"], 3)

	def test_a_different_action_resets_the_habit_rather_than_blending(self):
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Indiana Foods Inc", True)
		self._write("ordered_from:Bloomington Dairy", True)

		self.assertEqual(frappe.db.count("EORL Memory Record", {"run": self.run.name, "actor": self.actor.name}), 1)
		record = frappe.get_all(
			"EORL Memory Record", filters={"run": self.run.name, "actor": self.actor.name},
			fields=["action", "salience"],
		)[0]
		self.assertEqual(record.action, "ordered_from:Bloomington Dairy")
		self.assertAlmostEqual(record.salience, 0.1)
