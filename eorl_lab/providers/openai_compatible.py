import inspect
import json
import time

import frappe
import requests

from eorl_lab.erp.registry import get_tool
from eorl_lab.providers.base import ModelProvider, ModelRequest, ModelResponse

# Parameters a tool declares that the orchestrator injects itself
# (eorl_lab.runtime.orchestrator._call_tool_with_context) -- never shown
# to the model as something it can set, and never present in the JSON
# schema offered to it.
_INJECTED_PARAM_NAMES = {"_case", "_sender_slot", "_communication_policy"}

# V2 section 2.4: the scenario's latent ground truth is hidden from
# agents. Only these "public" fields of a case are ever shown to the
# model -- it can learn the rest (quality_probability, price, etc.)
# only by calling sensing tools, exactly like the deterministic policy.
_PUBLIC_CASE_FIELDS = ("case_id", "case_hash", "item_code", "company", "warehouse", "qty")


def _json_type(annotation) -> str:
	if annotation is float:
		return "number"
	if annotation is int:
		return "integer"
	return "string"


def _tool_schema(tool_name: str) -> dict:
	"""Builds an OpenAI-style function/tool schema by introspecting the
	registered tool's own signature, so the model only ever sees the
	parameters a human operator would see -- the framework-injected ones
	are filtered out by name, not by trusting the model to omit them."""
	fn = get_tool(tool_name)
	sig = inspect.signature(fn)
	properties, required = {}, []
	for name, param in sig.parameters.items():
		if name in _INJECTED_PARAM_NAMES:
			continue
		properties[name] = {"type": _json_type(param.annotation)}
		if param.default is inspect.Parameter.empty:
			required.append(name)
	description = (fn.__doc__ or tool_name).strip().split("\n")[0]
	return {
		"type": "function",
		"function": {
			"name": tool_name,
			"description": description,
			"parameters": {"type": "object", "properties": properties, "required": required},
		},
	}


def _public_case(case: dict) -> dict:
	return {k: case[k] for k in _PUBLIC_CASE_FIELDS if k in case}


class OpenAICompatibleProvider(ModelProvider):
	"""Real model provider (V2 section 8.1) speaking the OpenAI
	chat-completions wire format -- the lowest common denominator most
	self-hosted inference servers (vLLM, TGI, Ollama's OpenAI-compatible
	endpoint, LM Studio) and OpenAI itself all speak, so one
	implementation covers all of them via EORL Model Profile's
	base_url/model_name rather than one class per vendor.

	Ground truth is NEVER included in the prompt (V2 section 2.4) --
	only the case's public fields, this actor's own accumulated
	`scratch`, and retrieved memory are shown; the model can only learn
	hidden ground truth by calling sensing tools, exactly like the
	deterministic policy. Tool selection uses real OpenAI-style function
	calling (`tool_choice: required`), not JSON-in-prose parsing --
	verified against the actual vLLM/Qwen3 endpoint this was built
	against, which supports it natively."""

	def __init__(self, model_profile):
		self.profile = model_profile
		if not model_profile.base_url:
			frappe.throw(f"EORL Model Profile {model_profile.name!r}: base_url is required for provider 'openai_compatible'.")
		if not model_profile.model_name:
			frappe.throw(f"EORL Model Profile {model_profile.name!r}: model_name is required for provider 'openai_compatible'.")
		self.base_url = model_profile.base_url.rstrip("/")
		self.last_retry_count = 0
		self.model_name = model_profile.model_name
		self.api_key = frappe.conf.get(model_profile.api_key_reference) if model_profile.api_key_reference else None
		if not self.api_key:
			frappe.throw(
				f"EORL Model Profile {model_profile.name!r}: no secret found under "
				f"api_key_reference {model_profile.api_key_reference!r} in site config. "
				f"Set it with: bench --site <site> set-config {model_profile.api_key_reference} <key>"
			)

	def generate(self, request: ModelRequest) -> ModelResponse:
		tools = [_tool_schema(name) for name in request.available_tools]
		messages = self._build_messages(request)

		body = {
			"model": self.model_name,
			"messages": messages,
			"tools": tools,
			"tool_choice": "required",
			"max_tokens": self.profile.max_tokens or 600,
		}
		# Frappe Float fields read back as 0.0, never None, when left
		# blank on the doc -- indistinguishable from a deliberate 0.0 at
		# the Python level. temperature=0.0 is at least a coherent
		# ("greedy") request; top_p=0.0 is rejected outright by this
		# server ("must be in (0, 1]"), so omit it entirely unless a
		# real value is set rather than forwarding a false 0.0.
		if self.profile.temperature:
			body["temperature"] = self.profile.temperature
		if self.profile.top_p:
			body["top_p"] = self.profile.top_p
		if (self.profile.reasoning_mode_if_supported or "").strip().lower() == "disabled":
			# Qwen3/vLLM convention: suppresses the model's internal
			# reasoning trace entirely. Without this, a "thinking" model
			# can spend its whole max_tokens budget reasoning and return
			# finish_reason="length" with no tool call at all -- a real
			# failure mode this was hit by live during development.
			# Disabling it trades away the reasoning text this provider
			# otherwise surfaces as decision_basis/state_assessment for
			# much more reliable, lower-latency tool selection.
			body["chat_template_kwargs"] = {"enable_thinking": False}

		started = time.monotonic()
		payload = self._post_with_retries(body)
		latency_ms = (time.monotonic() - started) * 1000.0

		choice = payload["choices"][0]
		message = choice["message"]
		tool_calls = message.get("tool_calls") or []
		if not tool_calls:
			raise RuntimeError(
				f"OpenAICompatibleProvider: model returned no tool call "
				f"(finish_reason={choice.get('finish_reason')!r}); this provider requires "
				f"exactly one tool call per turn. Raw content: {message.get('content')!r}"
			)

		call = tool_calls[0]  # spec-driven: "call exactly one tool per turn"; extras are ignored, not merged.
		tool_name = call["function"]["name"]
		try:
			tool_args = json.loads(call["function"].get("arguments") or "{}")
		except json.JSONDecodeError as exc:
			raise RuntimeError(f"OpenAICompatibleProvider: model returned invalid JSON tool arguments: {exc}")

		reasoning = (message.get("reasoning") or "").strip()
		is_finish = tool_name == "finish_turn"

		decision = {
			"decision_version": "1.0",
			"state_assessment": reasoning or f"Decided to call {tool_name}.",
			"intended_action": tool_name,
			"tool_arguments": {} if is_finish else tool_args,
			"recipient": None,
			"confidence": 0.7,  # placeholder: this provider does not yet elicit a calibrated confidence from the model.
			"decision_basis": reasoning or f"Model-selected tool call: {tool_name}.",
			"stop": is_finish,
		}

		return ModelResponse(
			decision=decision,
			provider="openai_compatible",
			resolved_model=payload.get("model") or self.model_name,
			raw_text=message.get("content"),
			token_counts=payload.get("usage") or {},
			latency_ms=latency_ms,
			provider_request_id=payload.get("id"),
			retry_count=self.last_retry_count,
		)

	def _post_with_retries(self, body: dict) -> dict:
		last_exc = None
		attempts = max(1, self.profile.max_retries or 1)
		for attempt in range(attempts):
			self.last_retry_count = attempt
			try:
				resp = requests.post(
					f"{self.base_url}/chat/completions",
					headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
					json=body,
					timeout=self.profile.timeout_seconds or 120,
				)
				if not resp.ok:
					# Surface the server's own rejection reason (e.g. context
					# length exceeded, malformed schema) instead of just the
					# bare status code -- essential for diagnosing a live,
					# non-deterministic external model server.
					last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:1000]}")
					continue
				return resp.json()
			except (requests.RequestException, ValueError) as exc:
				last_exc = exc
		raise RuntimeError(f"OpenAICompatibleProvider: request to {self.base_url} failed after {attempts} attempt(s): {last_exc}")

	def _build_messages(self, request: ModelRequest) -> list:
		ctx = request.context
		role = ctx.get("organizational_role") or "agent"
		scratch = ctx.get("scratch") or {}
		system_parts = [
			request.system_instructions or "",
			f"You act as the organizational role: {role}.",
			"This is a fresh request with no memory of previous requests -- `already_observed` "
			"below is the ONLY record of what you have done and sensed so far this turn; it is "
			"not optional context, it is your working memory. Before choosing a tool, check "
			"whether `already_observed` already contains the result you would get from calling "
			"it again (e.g. if `candidate_suppliers` is already listed, do not call "
			"get_supplier_options again -- choose a supplier from that list and move on to the "
			"next step of the procedure instead). Call exactly one NEW tool this turn that "
			"advances the procedure past what `already_observed` already shows. When your role's "
			"part of this procedure is genuinely complete, call finish_turn instead of any other "
			"tool.",
		]
		user_payload = {
			"case": _public_case(ctx.get("case") or {}),
			"handoff_received": ctx.get("handoff") or {},
			"already_observed": scratch,
			"memory": [
				{"case_summary": m.get("case_summary"), "action": m.get("action"), "outcome": m.get("outcome")}
				for m in (ctx.get("memory") or [])
			],
		}
		return [
			{"role": "system", "content": "\n\n".join(p for p in system_parts if p)},
			{"role": "user", "content": json.dumps(user_payload)},
		]
