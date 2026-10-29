from dataclasses import dataclass, field
from typing import Optional

import frappe

# Milestone 2 only registers these two tools (eorl_lab.erp.registry); the
# split is used to decide which events/limits apply, independent of the
# registry itself so later milestones can extend both lists together.
READ_TOOLS = {"get_supplier_options"}
WRITE_TOOLS = {"create_purchase_order"}


@dataclass
class AuthorityDecision:
	allowed: bool
	reason_code: str
	policy_version: Optional[str] = None
	resolved_scope: dict = field(default_factory=dict)

	def as_dict(self):
		return {
			"allowed": self.allowed,
			"reason_code": self.reason_code,
			"policy_version": self.policy_version,
			"resolved_scope": self.resolved_scope,
		}


def evaluate(*, tool_policy_name: str, tool_name: str, tool_args: dict) -> AuthorityDecision:
	"""Deterministic authority check outside the model (spec section 9).
	The model may request anything; only this function decides what
	actually executes. Never driven by prompt text."""

	if not tool_policy_name or not frappe.db.exists("EORL Tool Policy", tool_policy_name):
		return AuthorityDecision(False, "NO_POLICY_BOUND")

	policy = frappe.get_doc("EORL Tool Policy", tool_policy_name)
	allowed_tools = {row.tool_name for row in policy.allowed_semantic_tools}

	if tool_name not in allowed_tools:
		return AuthorityDecision(
			False, "TOOL_NOT_IN_POLICY", policy.modified, {"allowed_tools": sorted(allowed_tools)}
		)

	if tool_name in WRITE_TOOLS:
		max_writes = policy.max_write_actions_per_episode or 0
		episode_write_count = tool_args.get("_episode_write_count", 0)
		if max_writes and episode_write_count >= max_writes:
			return AuthorityDecision(
				False,
				"WRITE_BUDGET_EXCEEDED",
				policy.modified,
				{"max_write_actions_per_episode": max_writes},
			)

	return AuthorityDecision(True, "POLICY_ALLOW", policy.modified, {"tool": tool_name})
