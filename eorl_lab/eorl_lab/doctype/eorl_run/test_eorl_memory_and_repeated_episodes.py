import json

import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.runtime.orchestrator import run_specialist_routine

ROLE_POLICIES = {
	"purchasing_agent": {
		"policy_name": "Test Purchasing Policy M4",
		"may_submit_documents": 0,
		"tools": ["get_supplier_options", "create_purchase_order"],
	},
	"purchasing_manager_agent": {
		"policy_name": "Test Purchasing Manager Policy M4",
		"may_submit_documents": 1,
		"may_approve": 1,
		"tools": ["get_purchase_order", "submit_purchase_order"],
	},
	"warehouse_agent": {
		"policy_name": "Test Warehouse Policy M4",
		"may_submit_documents": 1,
		"may_message_agents": 1,
		"tools": [
			"get_purchase_order", "create_purchase_receipt", "submit_purchase_receipt",
			"inspect_received_goods", "escalate_quality_exception", "message_agent",
		],
	},
	"accounts_payable_agent": {
		"policy_name": "Test Accounts Payable Policy M4",
		"may_submit_documents": 1,
		"tools": [
			"get_receipt_status",
			"create_purchase_invoice",
			"submit_purchase_invoice",
			"create_payment_entry",
			"submit_payment_entry",
		],
	},
}

ROLE_LABELS = {
	"purchasing_agent": "Purchasing Agent",
	"purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent",
	"accounts_payable_agent": "Accounts Payable Agent",
}


class TestEORLMemoryAndRepeatedEpisodes(FrappeTestCase):
	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M4",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)

		self.memory_profile = frappe.get_doc(
			{
				"doctype": "EORL Memory Profile",
				"profile_name": "Test Episodic Memory Profile M4",
				"local_memory_enabled": 1,
				"local_backend": "episodic",
				"local_top_k": 3,
				"recency_weight": 0.6,
				"outcome_weight": 0.4,
			}
		).insert(ignore_if_duplicate=True)

		self.agent_templates = {}
		for key, spec in ROLE_POLICIES.items():
			policy = frappe.get_doc(
				{
					"doctype": "EORL Tool Policy",
					"policy_name": spec["policy_name"],
					"may_submit_documents": spec.get("may_submit_documents", 0),
					"may_approve": spec.get("may_approve", 0),
					"may_message_agents": spec.get("may_message_agents", 0),
					"allowed_semantic_tools": [{"tool_name": t} for t in spec["tools"]],
				}
			).insert(ignore_if_duplicate=True)

			agent_doc = {
				"doctype": "EORL Agent Template",
				"template_name": f"Test {ROLE_LABELS[key]} M4",
				"organizational_role": ROLE_LABELS[key],
				"model_profile": self.model_profile.name,
				"tool_policy": policy.name,
			}
			# Only the Purchasing Agent gets memory in this test -- memory
			# is an explicit per-actor experimental condition (spec
			# section 14), not something every actor must have.
			if key == "purchasing_agent":
				agent_doc["memory_profile"] = self.memory_profile.name

			agent = frappe.get_doc(agent_doc).insert(ignore_if_duplicate=True)
			self.agent_templates[key] = agent.name

	def test_repeated_episodes_persist_actor_memory(self):
		result = run_specialist_routine(self.agent_templates, seed=42, episode_count=3)

		self.assertEqual(len(result["episodes"]), 3)
		for episode_outcome in result["episodes"]:
			self.assertTrue(episode_outcome["success"], episode_outcome.get("failure_reason"))

		run = frappe.get_doc("EORL Run", result["run"])
		self.assertEqual(run.status, "completed")
		self.assertEqual(run.current_episode, 3)

		purchasing_agent_name = self.agent_templates["purchasing_agent"]

		# One memory record per episode for the actor that has memory
		# configured -- actor identity (the template) is stable, memory
		# accumulates underneath it across episodes (spec section 8.4).
		memory_records = frappe.get_all(
			"EORL Memory Record",
			filters={"run": result["run"], "actor": purchasing_agent_name},
			fields=["episode", "action", "success"],
			order_by="creation asc",
		)
		self.assertEqual(len(memory_records), 3)
		self.assertTrue(all(r.success for r in memory_records))
		first_supplier = memory_records[0].action.split("ordered_from:")[1]

		# Episode 1 has nothing to recall yet.
		ep1_retrievals = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"], "event_type": "memory_retrieval", "actor_slot": "Purchasing Agent"},
			fields=["payload_json"],
			order_by="sequence_no asc",
		)
		self.assertGreaterEqual(len(ep1_retrievals), 3)  # one retrieval per episode for this actor
		self.assertEqual(json.loads(ep1_retrievals[0].payload_json)["count"], 0)

		# Episodes 2 and 3 retrieved something, and the Purchasing Agent's
		# own stated decision basis names routinization explicitly --
		# this is the causal check, not just "same supplier by luck" (the
		# read tool's result order is already stable regardless of
		# memory, so a coincidental match wouldn't prove memory drove it).
		for retrieval in ep1_retrievals[1:]:
			self.assertGreaterEqual(json.loads(retrieval.payload_json)["count"], 1)

		decisions = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"], "event_type": "decision_parsed", "actor_slot": "Purchasing Agent"},
			fields=["payload_json"],
			order_by="sequence_no asc",
		)
		self.assertEqual(len(decisions), 6)  # 2 decisions/episode (sense, then act) x 3 episodes
		act_decisions = [json.loads(d.payload_json) for d in decisions if json.loads(d.payload_json)["intended_action"] == "create_purchase_order"]
		self.assertEqual(len(act_decisions), 3)

		self.assertNotIn("repeat a remembered", act_decisions[0]["decision_basis"])
		for later_decision in act_decisions[1:]:
			self.assertIn("repeat a remembered", later_decision["decision_basis"])
			self.assertEqual(later_decision["tool_arguments"]["supplier"], first_supplier)

		# All three episodes' purchase orders really exist and really
		# used that same remembered supplier end to end.
		for episode_outcome in result["episodes"]:
			po = frappe.get_doc("Purchase Order", episode_outcome["purchase_order"])
			self.assertEqual(po.supplier, first_supplier)

	def test_actor_without_memory_profile_gets_no_memory_writes(self):
		result = run_specialist_routine(self.agent_templates, seed=42, episode_count=2)
		self.assertTrue(result["episodes"][-1]["success"])

		manager_name = self.agent_templates["purchasing_manager_agent"]
		manager_records = frappe.get_all(
			"EORL Memory Record", filters={"run": result["run"], "actor": manager_name}
		)
		self.assertEqual(len(manager_records), 0)

		# But memory_query/memory_retrieval events were still logged for
		# it -- an empty retrieval is still an observed, logged retrieval
		# (spec section 14: "every retrieval ... must be logged").
		manager_queries = frappe.get_all(
			"EORL Event",
			filters={"run": result["run"], "event_type": "memory_query", "actor_slot": "Purchasing Manager Agent"},
		)
		self.assertEqual(len(manager_queries), 2)  # once per episode
