import frappe

from eorl_lab.runtime.orchestrator import run_demo_episode


@frappe.whitelist()
def launch_demo_episode(agent_template: str, seed: int = 42):
	"""Milestone 2 demo entrypoint. Full Run Monitor / Experiment Studio
	launch flows (spec sections 7.5-7.6) arrive in a later milestone; until
	then this is reachable via frappe.call or `bench execute`."""
	frappe.only_for(["System Manager", "EORL Administrator", "EORL Researcher"])
	return run_demo_episode(agent_template, seed=int(seed))
