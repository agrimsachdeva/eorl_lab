import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.providers.base import ModelRequest
from eorl_lab.providers.deterministic import DeterministicProvider
from eorl_lab.providers.factory import get_provider_for_agent
from eorl_lab.providers.openai_compatible import OpenAICompatibleProvider, _public_case, _tool_schema
from eorl_lab.runtime.orchestrator import run_architecture

LIVE_QWEN_BASE_URL = "http://100.100.116.58:8000/v1"
LIVE_QWEN_MODEL = "barrydeen/Qwen3.8-27B-AWQ-4bit"

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options", "get_purchase_order", "get_receipt_status",
	"create_purchase_order", "submit_purchase_order", "create_purchase_receipt",
	"submit_purchase_receipt", "create_purchase_invoice", "submit_purchase_invoice",
	"create_payment_entry", "submit_payment_entry", "inspect_received_goods",
	"escalate_quality_exception", "message_agent", "finish_turn",
]


class TestProviderFactory(FrappeTestCase):
	"""SOTA Milestone 3: provider selection is per-agent (its own EORL
	Model Profile), not a single DeterministicProvider instance hard-
	coded once for the whole run (every prior milestone's actual
	behavior, despite the provider abstraction existing since
	Milestone 2)."""

	def _agent_with_profile(self, provider: str, **profile_kwargs):
		model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": f"Test Factory {provider} Profile {frappe.generate_hash(length=6)}",
				"provider": provider,
				"enabled": 1,
				**profile_kwargs,
			}
		).insert(ignore_permissions=True)
		tool_policy = frappe.get_doc(
			{"doctype": "EORL Tool Policy", "policy_name": f"Test Factory Tool Policy {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)
		return frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": f"Test Factory Agent {frappe.generate_hash(length=6)}",
				"organizational_role": "Purchasing Agent",
				"model_profile": model_profile.name,
				"tool_policy": tool_policy.name,
			}
		).insert(ignore_permissions=True)

	def test_deterministic_provider_dispatch(self):
		agent = self._agent_with_profile("deterministic")
		self.assertIsInstance(get_provider_for_agent(agent), DeterministicProvider)

	def test_openai_compatible_provider_dispatch(self):
		agent = self._agent_with_profile(
			"openai_compatible",
			base_url="http://100.100.116.58:8000/v1",
			model_name="barrydeen/Qwen3.8-27B-AWQ-4bit",
			api_key_reference="qwen_api_key",
		)
		self.assertIsInstance(get_provider_for_agent(agent), OpenAICompatibleProvider)

	def test_openai_compatible_provider_requires_api_key_reference_to_resolve(self):
		agent = self._agent_with_profile(
			"openai_compatible",
			base_url="http://100.100.116.58:8000/v1",
			model_name="barrydeen/Qwen3.8-27B-AWQ-4bit",
			api_key_reference="this_key_was_never_configured_in_site_config",
		)
		with self.assertRaises(frappe.ValidationError):
			get_provider_for_agent(agent)

	def test_unimplemented_provider_raises(self):
		agent = self._agent_with_profile("anthropic")
		with self.assertRaises(NotImplementedError):
			get_provider_for_agent(agent)

	def test_disabled_model_profile_blocks_dispatch(self):
		agent = self._agent_with_profile("deterministic", enabled=0)
		with self.assertRaises(frappe.ValidationError):
			get_provider_for_agent(agent)


class TestOpenAICompatibleProviderPromptConstruction(FrappeTestCase):
	"""Pure prompt-construction correctness -- no live network call.
	V2 section 2.4: latent ground truth is hidden from agents. These
	tests assert that guarantee directly against the actual messages
	this provider sends, not just against intent."""

	def _model_profile(self):
		return frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": f"Test Prompt Profile {frappe.generate_hash(length=6)}",
				"provider": "openai_compatible",
				"base_url": "http://100.100.116.58:8000/v1",
				"model_name": "barrydeen/Qwen3.8-27B-AWQ-4bit",
				"api_key_reference": "qwen_api_key",
			}
		).insert(ignore_permissions=True)

	def test_latent_ground_truth_never_reaches_the_prompt(self):
		case = {
			"case_id": "CASE-TEST-0001",
			"case_hash": "deadbeef",
			"item_code": "MILK-001",
			"company": "Hoosier Ice Cream",
			"warehouse": "Stores - HIC",
			"qty": 550,
			"latent_ground_truth": {
				"Bloomington Dairy": {"delivery_probability": 0.95, "quality_probability": 0.89, "price": 0.82},
			},
			"exception": {"family": "none", "severity": 0.0},
		}
		request = ModelRequest(
			system_instructions="You are a purchasing agent.",
			context={"organizational_role": "Purchasing Agent", "case": case, "handoff": {}, "scratch": {}, "memory": []},
			available_tools=["get_supplier_options"],
		)
		provider = OpenAICompatibleProvider(self._model_profile())
		messages = provider._build_messages(request)
		full_text = " ".join(m["content"] for m in messages)

		for leaked_term in ("latent_ground_truth", "quality_probability", "delivery_probability", "0.89", "0.82", "0.95"):
			self.assertNotIn(leaked_term, full_text, f"{leaked_term!r} must never reach the model prompt")
		self.assertIn("MILK-001", full_text)
		self.assertIn("550", full_text)

	def test_public_case_strips_latent_ground_truth(self):
		case = {"case_id": "C1", "item_code": "MILK-001", "latent_ground_truth": {"x": 1}, "exception": {}}
		public = _public_case(case)
		self.assertNotIn("latent_ground_truth", public)
		self.assertNotIn("exception", public)
		self.assertEqual(public["item_code"], "MILK-001")

	def test_tool_schema_excludes_framework_injected_parameters(self):
		schema = _tool_schema("inspect_received_goods")
		properties = schema["function"]["parameters"]["properties"]
		self.assertIn("purchase_receipt", properties)
		self.assertNotIn("_case", properties)

	def test_tool_schema_excludes_communication_injected_parameters(self):
		schema = _tool_schema("message_agent")
		properties = schema["function"]["parameters"]["properties"]
		self.assertIn("recipient_slot", properties)
		self.assertIn("content", properties)
		self.assertNotIn("_sender_slot", properties)
		self.assertNotIn("_communication_policy", properties)

	def test_finish_turn_is_a_real_registered_tool_with_empty_schema(self):
		schema = _tool_schema("finish_turn")
		self.assertEqual(schema["function"]["parameters"]["properties"], {})
		self.assertEqual(schema["function"]["parameters"]["required"], [])

	def test_falsy_top_p_and_temperature_are_never_forwarded(self):
		# A blank Float field on an EORL Model Profile can read back as
		# 0.0 or None depending on how the doc was built -- either way,
		# this server rejects top_p=0.0 outright ("must be in (0, 1]").
		# Regression test for the actual incident hit live: forward
		# neither field unless a real, truthy value was configured.
		profile = self._model_profile()  # leaves temperature/top_p unset
		self.assertFalse(profile.temperature)
		self.assertFalse(profile.top_p)

		provider = OpenAICompatibleProvider(profile)
		request = ModelRequest(
			system_instructions="",
			context={"organizational_role": "Purchasing Agent", "case": {}, "scratch": {}, "memory": []},
			available_tools=["finish_turn"],
		)
		captured = {}

		def fake_post(url, headers=None, json=None, timeout=None):
			captured["body"] = json
			response = frappe._dict(ok=True)
			response.json = lambda: {
				"choices": [{"message": {"tool_calls": [{"function": {"name": "finish_turn", "arguments": "{}"}}]}}],
			}
			return response

		import eorl_lab.providers.openai_compatible as module

		original_post = module.requests.post
		module.requests.post = fake_post
		try:
			provider.generate(request)
		finally:
			module.requests.post = original_post

		self.assertNotIn("temperature", captured["body"])
		self.assertNotIn("top_p", captured["body"])


class TestLiveQwenEpisode(FrappeTestCase):
	"""SOTA Milestone 3's flagship proof: a REAL model, not
	DeterministicProvider, autonomously driving a full broad-autonomy
	procure-to-pay episode end to end against the live site, through
	genuine OpenAI-style tool calling against the actual vLLM/Qwen3
	endpoint this provider was built against. This hits a real external
	server over the tailnet -- not mocked, by design, matching this
	project's established practice of verifying every milestone against
	a real run rather than a simulated one."""

	def setUp(self):
		self.model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Live Qwen Model Profile",
				"provider": "openai_compatible",
				"enabled": 1,
				"base_url": LIVE_QWEN_BASE_URL,
				"model_name": LIVE_QWEN_MODEL,
				"api_key_reference": "qwen_api_key",
				"max_tokens": 1200,
				"timeout_seconds": 90,
				"max_retries": 2,
			}
		).insert(ignore_permissions=True)

		self.tool_policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Live Qwen Tool Policy",
				"may_submit_documents": 1,
				"may_approve": 1,
				"may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_permissions=True)

		self.agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test Live Qwen Purchasing Agent",
				"organizational_role": "General Purchasing Agent",
				"model_profile": self.model_profile.name,
				"tool_policy": self.tool_policy.name,
				"initial_system_instructions": (
					"You are an autonomous purchasing agent operating against a real ERPNext "
					"system. You have no information about suppliers, prices, or quality except "
					"what tool results tell you. Work through: sense supplier options, create and "
					"submit a purchase order, create and submit a purchase receipt, inspect "
					"received goods, create and submit a purchase invoice, create and submit a "
					"payment entry, then call finish_turn."
				),
			}
		).insert(ignore_permissions=True)

		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Live Qwen Broad Autonomy",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": self.agent.name}],
			}
		).insert(ignore_permissions=True)

	def test_real_model_autonomously_completes_a_full_procure_to_pay_episode(self):
		result = run_architecture(self.architecture.name, seed=909, episode_count=1)

		self.assertTrue(result["outcome"]["success"], result["outcome"].get("failure_reason"))
		self.assertIsNotNone(result["outcome"]["purchase_order"])
		self.assertIsNotNone(result["outcome"]["payment_entry"])

		po = frappe.get_doc("Purchase Order", result["outcome"]["purchase_order"])
		self.assertGreater(po.grand_total, 0, "rate must resolve from ground truth, not default to 0")

		events = frappe.get_all(
			"EORL Event", filters={"run": result["run"]},
			fields=["event_type", "target_id"], order_by="sequence_no asc",
		)
		model_responses = [e for e in events if e.event_type == "model_response"]
		self.assertGreater(len(model_responses), 0)

		tool_sequence = [e.target_id for e in events if e.event_type == "tool_result"]
		# The model chose this order itself; it is asserted as a SET of
		# required stages, not an exact sequence, since a real model is
		# free to take a different (still valid) path.
		for required in ("create_purchase_order", "submit_purchase_order", "create_payment_entry", "submit_payment_entry"):
			self.assertIn(required, tool_sequence)
		self.assertEqual(tool_sequence[-1], "finish_turn", "the model itself must decide to end its own turn")
