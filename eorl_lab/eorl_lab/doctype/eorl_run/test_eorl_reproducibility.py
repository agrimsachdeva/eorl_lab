import json
import zipfile
from io import BytesIO

import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.observability.exporter import build_full_bundle_zip
from eorl_lab.observability.replay import reproduce_run
from eorl_lab.runtime.orchestrator import run_architecture, run_specialist_routine

SPECIALIST_ROLE_POLICIES = {
	"purchasing_agent": {"may_submit_documents": 0, "tools": ["get_supplier_options", "create_purchase_order"]},
	"purchasing_manager_agent": {"may_submit_documents": 1, "tools": ["get_purchase_order", "submit_purchase_order"]},
	"warehouse_agent": {
		"may_submit_documents": 1,
		"tools": ["get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt"],
	},
	"accounts_payable_agent": {
		"may_submit_documents": 1,
		"tools": [
			"get_receipt_status", "create_purchase_invoice", "submit_purchase_invoice",
			"create_payment_entry", "submit_payment_entry",
		],
	},
}
SPECIALIST_ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent",
	"purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent",
	"accounts_payable_agent": "Accounts Payable Agent",
}


class TestEORLReproducibility(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M8",
				"provider": "deterministic",
				"model_name": "deterministic-v1",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		specialist_slots = []
		for key, spec in SPECIALIST_ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": f"Test {key} Policy M8",
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)
			agent = frappe.get_doc(
				{
					"doctype": "EORL Agent Template",
					"template_name": f"Test {SPECIALIST_ROLE_LABELS[key]} M8",
					"organizational_role": SPECIALIST_ROLE_LABELS[key],
					"model_profile": self.model_profile.name,
					"tool_policy": policy.name,
				}
			).insert(ignore_if_duplicate=True)
			specialist_slots.append({"slot_id": key, "agent_template": agent.name})
			self.agent_templates = getattr(self, "agent_templates", {})
			self.agent_templates[key] = agent.name

		self.specialist_architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Specialist Handoff M8",
				"coordination_mode": "specialist_handoff",
				"actor_slots": specialist_slots,
			}
		).insert(ignore_if_duplicate=True)

		self.regime_shift = frappe.get_doc(
			{
				"doctype": "EORL Regime Shift",
				"shift_name": "Test Demand Shock M8",
				"trigger_episode": 2,
				"parameter_delta_json": frappe.as_json({"qty_multiplier": 1.8}),
			}
		).insert(ignore_if_duplicate=True)

	def test_full_bundle_contains_every_promised_file_with_sane_content(self):
		result = run_architecture(
			self.specialist_architecture.name, seed=321, episode_count=2, regime_shift=self.regime_shift.name
		)
		self.assertTrue(result["outcome"]["success"])

		zip_bytes = build_full_bundle_zip(result["run"])
		with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
			names = set(zf.namelist())

			for expected in [
				"run_manifest.json", "architecture.json", "scenario_stream.jsonl",
				"events.jsonl", "process_paths.csv", "metrics.csv", "model_metadata.json",
				"environment_metadata.json", "code_commit.txt", "requirements_lock.txt",
				"README_REPRODUCE.md",
			]:
				self.assertIn(expected, names)

			resolved_configs = [n for n in names if n.startswith("resolved_agent_configs/")]
			self.assertEqual(len(resolved_configs), 4)  # one per specialist slot

			manifest = json.loads(zf.read("run_manifest.json"))
			self.assertEqual(manifest["run_id"], result["run"])
			self.assertEqual(manifest["seed"], 321)
			self.assertEqual(manifest["architecture"]["name"], self.specialist_architecture.name)
			self.assertEqual(len(manifest["scenario_case_hashes"]), 2)

			scenario_lines = zf.read("scenario_stream.jsonl").decode().strip().split("\n")
			self.assertEqual(len(scenario_lines), 2)
			case_1 = json.loads(scenario_lines[0])
			self.assertEqual(case_1["case_hash"], manifest["scenario_case_hashes"][0])

			metrics_csv = zf.read("metrics.csv").decode()
			self.assertIn("actor_switch_rate", metrics_csv)

			model_metadata = json.loads(zf.read("model_metadata.json"))
			self.assertIn(self.model_profile.name, model_metadata)
			self.assertNotIn("api_key_reference", json.dumps(model_metadata))

	def test_reproduce_run_matches_scenario_hashes_and_metrics(self):
		original = run_architecture(
			self.specialist_architecture.name, seed=654, episode_count=3, regime_shift=self.regime_shift.name
		)
		self.assertTrue(original["outcome"]["success"])

		result = reproduce_run(original["run"])

		self.assertNotEqual(result["reproduction_run"], original["run"])
		self.assertTrue(result["scenario_stream_matches"])
		self.assertTrue(result["metrics_match"], result["mismatched_metrics"])
		self.assertEqual(result["original_status"], "completed")
		self.assertTrue(result["reproduction_status"])

		# The reproduction really did create a second, independent run
		# with its own real ERP documents -- not a no-op.
		reproduction_episode = frappe.get_doc("EORL Episode", f"{result['reproduction_run']}-EP-1")
		original_episode = frappe.get_doc("EORL Episode", f"{original['run']}-EP-1")
		self.assertNotEqual(reproduction_episode.name, original_episode.name)
		self.assertEqual(reproduction_episode.scenario_case_id, original_episode.scenario_case_id)

	def test_reproduce_run_refuses_runs_without_architecture_name(self):
		"""Honest limitation, enforced: run_specialist_routine-created
		runs don't carry an architecture name in their snapshot, so
		reproduce_run must refuse rather than guess."""
		legacy_result = run_specialist_routine(self.agent_templates, seed=1, episode_count=1)
		self.assertTrue(legacy_result["outcome"]["success"])

		with self.assertRaises(frappe.ValidationError):
			reproduce_run(legacy_result["run"])
