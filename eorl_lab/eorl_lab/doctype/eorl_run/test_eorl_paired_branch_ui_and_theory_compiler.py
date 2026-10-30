import frappe
from frappe.tests.utils import FrappeTestCase

from eorl_lab.api.experiments import compile_theory
from eorl_lab.api.runs import list_branch_groups
from eorl_lab.runtime.orchestrator import branch_run, run_architecture

BROAD_AUTONOMY_TOOLS = [
	"get_supplier_options",
	"get_purchase_order",
	"get_receipt_status",
	"create_purchase_order",
	"submit_purchase_order",
	"create_purchase_receipt",
	"submit_purchase_receipt",
	"create_purchase_invoice",
	"submit_purchase_invoice",
	"create_payment_entry",
	"submit_payment_entry",
	"inspect_received_goods",
	"escalate_quality_exception",
	"message_agent",
]


class TestEORLPairedBranchGroups(FrappeTestCase):
	"""SOTA Milestone 10 (V2 section 44.3): the dedicated paired-branch
	inference UI's backend, which groups an EORL Run's branches by their
	shared source_episode -- the genuine sibling sets a paired comparison
	is allowed to treat as matched."""

	def setUp(self):
		model_profile = frappe.get_doc(
			{
				"doctype": "EORL Model Profile",
				"profile_name": "Test Deterministic Profile M10Branch",
				"provider": "deterministic",
				"enabled": 1,
			}
		).insert(ignore_if_duplicate=True)
		policy = frappe.get_doc(
			{
				"doctype": "EORL Tool Policy",
				"policy_name": "Test Broad Autonomy Policy M10Branch",
				"may_submit_documents": 1,
				"may_approve": 1,
				"may_message_agents": 1,
				"allowed_semantic_tools": [{"tool_name": t} for t in BROAD_AUTONOMY_TOOLS],
			}
		).insert(ignore_if_duplicate=True)
		agent = frappe.get_doc(
			{
				"doctype": "EORL Agent Template",
				"template_name": "Test General Purchasing Agent M10Branch",
				"organizational_role": "General Purchasing Agent",
				"model_profile": model_profile.name,
				"tool_policy": policy.name,
			}
		).insert(ignore_if_duplicate=True)
		self.architecture = frappe.get_doc(
			{
				"doctype": "EORL Architecture",
				"architecture_name": "Test Broad Autonomy M10Branch",
				"coordination_mode": "broad_autonomy",
				"actor_slots": [{"slot_id": "general_purchasing_agent", "agent_template": agent.name}],
			}
		).insert(ignore_if_duplicate=True)

	def test_groups_branches_by_shared_source_episode(self):
		parent = run_architecture(self.architecture.name, seed=81, episode_count=2)
		self.assertTrue(parent["outcome"]["success"])

		pair_a = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.architecture.name, intervention_description="pair at ep2, variant A",
		)
		pair_b = branch_run(
			parent["run"], branch_episode=2, additional_episode_count=1,
			architecture_name=self.architecture.name, intervention_description="pair at ep2, variant B",
		)
		lone = branch_run(
			parent["run"], branch_episode=1, additional_episode_count=1,
			architecture_name=self.architecture.name, intervention_description="solo at ep1",
		)

		result = list_branch_groups(parent["run"])
		self.assertEqual(result["parent_run"], parent["run"])
		self.assertEqual(set(result["groups"].keys()), {1, 2})

		group_at_2 = {b["child_run"] for b in result["groups"][2]}
		self.assertEqual(group_at_2, {pair_a["branch_run"], pair_b["branch_run"]})
		self.assertEqual(len(result["groups"][1]), 1)
		self.assertEqual(result["groups"][1][0]["child_run"], lone["branch_run"])

		descriptions = {b["intervention_description"] for b in result["groups"][2]}
		self.assertEqual(descriptions, {"pair at ep2, variant A", "pair at ep2, variant B"})

	def test_run_with_no_branches_returns_empty_groups(self):
		parent = run_architecture(self.architecture.name, seed=82, episode_count=1)
		result = list_branch_groups(parent["run"])
		self.assertEqual(result["groups"], {})


class TestEORLTheoryCompiler(FrappeTestCase):
	"""SOTA Milestone 10 (V2 section 21): a structured wizard that
	scaffolds a real EORL Experiment + EORL Analysis Plan from a filled-in
	theory -- explicitly NOT autonomous theory generation."""

	def test_compile_theory_with_focal_construct_autofills_outcome_metric(self):
		result = compile_theory(
			focal_construct="Routine coherence",
			experiment_name="M10 Test Theory A",
			theoretical_definition="Routines become more coherent with repetition.",
			proposed_mechanism="Repeated joint action stabilizes actor sequencing.",
			manipulation="Vary episode_count.",
			counterfactual_condition="No repetition (single episode).",
			outcomes="actor_continuity",
			mediating_measures="",
			boundary_conditions="",
		)
		self.addCleanup(frappe.delete_doc, "EORL Experiment", result["experiment"], force=True)
		self.addCleanup(frappe.delete_doc, "EORL Analysis Plan", result["analysis_plan"], force=True)

		self.assertTrue(result["outcome_metric_guessed"])
		experiment = frappe.get_doc("EORL Experiment", result["experiment"])
		self.assertEqual(experiment.focal_construct, "Routine coherence")
		self.assertEqual(experiment.research_question, "Routines become more coherent with repetition.")
		self.assertEqual(experiment.status, "draft")

		plan = frappe.get_doc("EORL Analysis Plan", result["analysis_plan"])
		self.assertEqual(plan.experiment, experiment.name)
		self.assertEqual(plan.outcome_metric, "actor_continuity")
		self.assertEqual(plan.analysis_unit, "run")

	def test_compile_theory_without_focal_construct_leaves_outcome_metric_as_explicit_placeholder(self):
		result = compile_theory(
			focal_construct=None,
			experiment_name="M10 Test Theory B",
			theoretical_definition="Some untested theory.",
			proposed_mechanism="Unknown mechanism.",
			manipulation="",
			counterfactual_condition="",
			outcomes="",
			mediating_measures="",
			boundary_conditions="",
		)
		self.addCleanup(frappe.delete_doc, "EORL Experiment", result["experiment"], force=True)
		self.addCleanup(frappe.delete_doc, "EORL Analysis Plan", result["analysis_plan"], force=True)

		self.assertFalse(result["outcome_metric_guessed"])
		plan = frappe.get_doc("EORL Analysis Plan", result["analysis_plan"])
		self.assertIn("UNSET", plan.outcome_metric)

	def test_compile_theory_refuses_duplicate_experiment_name(self):
		result = compile_theory(
			focal_construct=None, experiment_name="M10 Test Theory Dup",
			theoretical_definition="x", proposed_mechanism="x",
			manipulation="", counterfactual_condition="", outcomes="",
			mediating_measures="", boundary_conditions="",
		)
		self.addCleanup(frappe.delete_doc, "EORL Experiment", result["experiment"], force=True)
		self.addCleanup(frappe.delete_doc, "EORL Analysis Plan", result["analysis_plan"], force=True)

		with self.assertRaises(frappe.ValidationError):
			compile_theory(
				focal_construct=None, experiment_name="M10 Test Theory Dup",
				theoretical_definition="y", proposed_mechanism="y",
				manipulation="", counterfactual_condition="", outcomes="",
				mediating_measures="", boundary_conditions="",
			)
