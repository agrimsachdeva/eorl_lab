from dataclasses import dataclass, field
from typing import List, Optional

import frappe

# Milestone 3 extended the read/write split to cover the full
# procure-to-pay chain (spec section 10); SOTA Milestone 1 adds the
# ground-truth-driven inspection/exception tools and the agent-chosen
# communication tool (V2 sections 9, 15). The split only decides which
# events/limits apply -- the actual allow/deny is always the per-actor
# EORL Tool Policy's allowed_semantic_tools, never this set membership.
READ_TOOLS = {"get_supplier_options", "get_purchase_order", "get_receipt_status", "inspect_received_goods"}
WRITE_TOOLS = {
	"create_purchase_order",
	"submit_purchase_order",
	"create_purchase_receipt",
	"submit_purchase_receipt",
	"create_purchase_invoice",
	"submit_purchase_invoice",
	"create_payment_entry",
	"submit_payment_entry",
	"escalate_quality_exception",
}
# Neither read nor write for budget purposes -- a message is its own
# category (V2 section 9), gated by may_message_agents, not by the
# write-action budget.
COMMUNICATION_TOOLS = {"message_agent"}

# SOTA Milestone 1 (V2 section 13): a soft rule is logged but never
# blocks execution. Currently one concrete rule, not a general rule DSL
# -- see EORL Tool Policy.soft_rule_large_qty_threshold.
SOFT_RULE_QTY_TOOLS = {"create_purchase_order"}


@dataclass
class AuthorityDecision:
	allowed: bool
	reason_code: str
	policy_version: Optional[str] = None
	resolved_scope: dict = field(default_factory=dict)
	soft_violations: List[str] = field(default_factory=list)

	def as_dict(self):
		return {
			"allowed": self.allowed,
			"reason_code": self.reason_code,
			"policy_version": self.policy_version,
			"resolved_scope": self.resolved_scope,
			"soft_violations": self.soft_violations,
		}


def _soft_violations(policy, tool_name: str, tool_args: dict) -> List[str]:
	violations = []
	if tool_name in SOFT_RULE_QTY_TOOLS and policy.soft_rule_large_qty_threshold:
		qty = tool_args.get("qty")
		if qty is not None and qty > policy.soft_rule_large_qty_threshold:
			violations.append("large_order_requires_manager_preapproval")
	return violations


def evaluate(*, tool_policy_name: str, tool_name: str, tool_args: dict) -> AuthorityDecision:
	"""Deterministic authority check outside the model (spec section 9).
	The model may request anything; only this function decides what
	actually executes. Never driven by prompt text.

	Hard constraints (V2 section 13) return allowed=False and block the
	call. Soft rules never block -- they're returned as
	`soft_violations` on an otherwise-allowed decision; the caller is
	responsible for logging them as an observable organizational event
	rather than silently proceeding."""

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

	if tool_name.startswith("submit_") and not policy.may_submit_documents:
		return AuthorityDecision(False, "SUBMIT_NOT_PERMITTED", policy.modified, {"tool": tool_name})

	if tool_name in COMMUNICATION_TOOLS and not policy.may_message_agents:
		return AuthorityDecision(False, "MESSAGING_NOT_PERMITTED", policy.modified, {"tool": tool_name})

	return AuthorityDecision(
		True, "POLICY_ALLOW", policy.modified, {"tool": tool_name},
		soft_violations=_soft_violations(policy, tool_name, tool_args),
	)
