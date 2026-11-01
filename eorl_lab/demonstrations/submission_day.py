"""Submission-day demonstration runs (plan section 31).

Four small designs that show the instrument working. None is a test of
the theory; each experiment is typed and labeled accordingly.

  SD-A  infrastructure_validation  scripted, specialist vs broad, matched exogenous outcomes
  SD-B  theory_demonstration       bounded-rational broad autonomy, memory vs no memory,
                                   matched branches from shared pre-shock histories
  SD-C  theory_demonstration       bounded-rational specialist vs broad vs broad with matched
                                   tools, under a supplier-quality reversal
  SD-D  infrastructure_validation  scripted order-to-cash, the second routine

setup() is idempotent and stores every Experiment and Analysis Plan
before any run exists. run_all() launches the runs; analyze() applies
the stored plans. Run them in that order with `bench execute`, one at a
time against a site.

The tool policies are the scripted ones already on the demonstration
site (pilot/demo_seed.py). On another site, pass `policy_names` to
setup() or create policies with the same names first.
"""
import frappe

from eorl_lab.routines import seed_routine_templates
from eorl_lab.scenarios.order_to_cash import ensure_master_data

DEMONSTRATION_1 = "Demonstration 1: Agentic Routinization and Adaptive Repertoire"
LABEL = "Demonstration / proof of capability. Not a test of the theory."

SHOCK = "Supplier Quality Reversal at Episode 7"
SHOCK_DELTA = {
	"pre_shock_latent_ground_truth": {
		"Bloomington Dairy": {"quality_probability": 0.95, "delivery_probability": 0.95},
		"Indiana Foods Inc": {"quality_probability": 0.78, "delivery_probability": 0.80},
	},
	"post_shock_latent_ground_truth": {
		"Bloomington Dairy": {"quality_probability": 0.58, "delivery_probability": 0.60},
		"Indiana Foods Inc": {"quality_probability": 0.91, "delivery_probability": 0.92},
	},
}

P2P_POLICIES = {
	"purchasing_agent": "Purchasing Agent Policy",
	"purchasing_manager_agent": "Purchasing Manager Agent Policy",
	"warehouse_agent": "Warehouse Agent Policy",
	"accounts_payable_agent": "Accounts Payable Agent Policy",
	"general_purchasing_agent": "General Purchasing Policy",
}
P2P_ROLES = {
	"purchasing_agent": "Purchasing Agent", "purchasing_manager_agent": "Purchasing Manager Agent",
	"warehouse_agent": "Warehouse Agent", "accounts_payable_agent": "Accounts Payable Agent",
	"general_purchasing_agent": "General Purchasing Agent",
}
O2C_TOOLS = {
	"sales_agent": ("Sales Agent", ["get_customer_order", "create_sales_order", "submit_sales_order"]),
	"fulfillment_agent": ("Fulfillment Agent", ["get_sales_order", "create_delivery_note", "submit_delivery_note"]),
	"billing_agent": ("Billing Agent", ["get_delivery_status", "create_sales_invoice", "submit_sales_invoice",
		"create_customer_payment", "submit_customer_payment"]),
}

SEEDS = [8101, 8102, 8103, 8104, 8105]


def _ensure(doctype: str, name_field: str, values: dict):
	name = values[name_field]
	if frappe.db.exists(doctype, name):
		return frappe.get_doc(doctype, name)
	return frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def _agent(name, role, policy, memory_profile, model_profile):
	return _ensure("EORL Agent Template", "template_name", {
		"template_name": name, "organizational_role": role, "enabled": 1, "model_profile": model_profile,
		"memory_profile": memory_profile, "tool_policy": policy,
		"role_description": f"{role} ({LABEL})",
	}).name


def _architecture(name, mode, slots, description, routine=None, stage_gated=0):
	return _ensure("EORL Architecture", "architecture_name", {
		"architecture_name": name, "coordination_mode": mode, "description": description,
		"routine_template": routine, "stage_gated_tools": stage_gated,
		"actor_slots": [{"slot_id": s, "agent_template": a} for s, a in slots.items()],
	}).name


def _plan(name, experiment, metric, expected, *, family=None, paired=False, bounds=None, scope="all_actions",
	question="", equivalence_rule="inconsistent"):
	return _ensure("EORL Analysis Plan", "plan_name", {
		"plan_name": name, "version": "1", "experiment": experiment, "research_question": question,
		"outcome_metric": metric, "analysis_unit": "run", "sequence_scope": scope,
		"paired_by": "branch_point" if paired else None, "model_family": "paired_t" if paired else "welch_t",
		"alpha": 0.05, "permutation_iterations": 10000, "bootstrap_iterations": 5000, "random_seed": 20261101,
		"equivalence_bounds": bounds, "multiple_testing_family": family, "adjustment_method": "holm" if family else "none",
		"expected_direction": expected, "support_rule": "consistent", "contradiction_rule": "inconsistent",
		"equivalence_rule": equivalence_rule, "inconclusive_rule": "inconclusive", "trivial_effect_rule": "inconclusive",
	}).name


def setup(policy_names: dict = None) -> dict:
	policies = {**P2P_POLICIES, **(policy_names or {})}
	seed_routine_templates()
	ensure_master_data()

	scripted = _ensure("EORL Model Profile", "profile_name", {"profile_name": "Scripted Policy", "provider": "deterministic", "enabled": 1}).name
	bounded = _ensure("EORL Model Profile", "profile_name", {"profile_name": "Bounded-Rational Policy", "provider": "bounded_rational", "enabled": 1}).name
	memory = _ensure("EORL Memory Profile", "profile_name", {
		"profile_name": "Episodic Memory (k=3)", "local_memory_enabled": 1, "local_backend": "episodic", "local_top_k": 3,
		"recency_weight": 1.0, "outcome_weight": 0.0,
	}).name
	no_memory = _ensure("EORL Memory Profile", "profile_name", {"profile_name": "No Memory", "local_memory_enabled": 0, "local_backend": "none"}).name

	_ensure("EORL Regime Shift", "shift_name", {
		"shift_name": SHOCK, "trigger_episode": 7, "shift_type": "abrupt", "hidden_from_agents": 1,
		"description": "Path-invalidating shock: the previously better supplier becomes the worse one.",
		"expected_observable_change": "More quality exceptions on the previously dominant supplier; adaptation requires changing supplier.",
		"parameter_delta_json": frappe.as_json(SHOCK_DELTA),
	})

	# Procure-to-pay agents: bound to the bounded-rational profile, with memory.
	sd = {slot: _agent(f"SD {role}", role, policies[slot], memory, bounded) for slot, role in P2P_ROLES.items()}
	sd_broad_nomem = _agent("SD General Purchasing Agent (no memory)", "General Purchasing Agent", policies["general_purchasing_agent"], no_memory, bounded)
	specialist_slots = {k: v for k, v in sd.items() if k != "general_purchasing_agent"}

	archs = {
		"specialist": _architecture("SD Specialist Handoff", "specialist_handoff", specialist_slots,
			"Four role-bounded actors with episodic memory; orchestrator-enforced handoffs."),
		"broad": _architecture("SD Broad Autonomy", "broad_autonomy", {"general_purchasing_agent": sd["general_purchasing_agent"]},
			"One actor with every procure-to-pay tool and episodic memory."),
		"broad_nomem": _architecture("SD Broad Autonomy (no memory)", "broad_autonomy", {"general_purchasing_agent": sd_broad_nomem},
			"Identical to SD Broad Autonomy except that memory is disabled."),
		"broad_matched": _architecture("SD Broad Autonomy, Matched Tools", "broad_autonomy", {"general_purchasing_agent": sd["general_purchasing_agent"]},
			"One actor, but at each step only the tools of the current stage are offered and authorized: the same tool ecology as the specialists.",
			stage_gated=1),
	}

	# Order-to-cash: scripted, three specialists and one broad actor.
	o2c_policies = {}
	for slot, (role, tools) in O2C_TOOLS.items():
		o2c_policies[slot] = _ensure("EORL Tool Policy", "policy_name", {
			"policy_name": f"O2C {role} Policy", "may_submit_documents": 1,
			"allowed_semantic_tools": [{"tool_name": t} for t in tools],
		}).name
	o2c_broad_policy = _ensure("EORL Tool Policy", "policy_name", {
		"policy_name": "O2C General Order Policy", "may_submit_documents": 1, "may_approve": 1,
		"allowed_semantic_tools": [{"tool_name": t} for _r, tools in O2C_TOOLS.values() for t in tools],
	}).name
	o2c_agents = {slot: _agent(f"O2C {role}", role, o2c_policies[slot], None, scripted) for slot, (role, _t) in O2C_TOOLS.items()}
	o2c_broad = _agent("O2C General Order Agent", "General Order Agent", o2c_broad_policy, None, scripted)
	archs["o2c_specialist"] = _architecture("O2C Specialist Handoff", "specialist_handoff", o2c_agents,
		"Order-to-cash with three role-bounded actors.", routine="Order-to-Cash")
	archs["o2c_broad"] = _architecture("O2C Broad Autonomy", "broad_autonomy", {"general_order_agent": o2c_broad},
		"Order-to-cash with one actor holding every tool.", routine="Order-to-Cash")

	experiments = _register_experiments(archs)
	_label_existing_experiments()
	frappe.db.commit()
	return {"architectures": archs, "experiments": experiments}


def _experiment(name, **values):
	return _ensure("EORL Experiment", "experiment_name", {"experiment_name": name, "status": "validated", "seed_strategy": "paired",
		"base_seed": SEEDS[0], **values}).name


def _register_experiments(archs) -> dict:
	a = _experiment(
		"SD-A Matched Exogenous Outcomes (scripted)", experiment_type="infrastructure_validation",
		research_question="Does the same action under two architectures meet the same exogenous outcome?",
		architecture_a=archs["specialist"], architecture_b=archs["broad"], episode_count=6, repetitions_per_cell=5,
		actor_engine="scripted_deterministic", primary_outcomes="Per-episode inspection outcome match rate (must be 1.0).",
		notes=f"{LABEL} Infrastructure validation of the matched outcome model (plan section 21).",
	)
	_plan("SD-A manipulation check: actor continuity", a, "actor_continuity", "b_greater",
		question="Broad autonomy has higher actor continuity by construction.")
	_plan("SD-A all-action vs consequential entropy (specialist minus broad)", a, "sequence_entropy", "nonzero",
		scope="consequential_actions", bounds="-0.65,0.65", equivalence_rule="consistent",
		question="With scripted actors and matched outcomes, consequential-action variety should not differ between arms.")

	b = _experiment(
		"SD-B Memory Manipulation under Supplier Reversal (bounded-rational, branched)", experiment_type="theory_demonstration",
		demonstration=DEMONSTRATION_1,
		research_question="Does actor memory change post-shock performance when everything else is held fixed?",
		theoretical_mechanism="Memory lets an actor accumulate feedback about which supplier now fails; without it the pre-shock routine persists.",
		architecture_a=archs["broad"], architecture_b=archs["broad_nomem"], regime_shift=SHOCK, episode_count=6, repetitions_per_cell=5,
		actor_engine="bounded_rational", interpretation_combination="AND",
		primary_outcomes="Mean post-shock utility of each branch (paired by shared pre-shock parent).",
		pre_registered_hypotheses="H-B1: branches with memory have higher post-shock utility than matched branches without memory.",
		notes=f"{LABEL} Five parents run episodes 1-6 (pre-shock) with memory; each is branched at episode 6 into a memory and a no-memory child that run episodes 7-12 after the shock.",
	)
	_plan("SD-B memory: post-shock mean utility (paired)", b, "mean_utility", "a_greater", paired=True, family="SD-B",
		bounds="-0.02,0.02", question="Memory branch minus no-memory branch.")
	_plan("SD-B memory: post-shock path concentration (paired)", b, "modal_path_share", "b_greater", paired=True,
		family="SD-B", scope="consequential_actions", question="Without memory the pre-shock sourcing path persists; with memory some branches switch supplier, so concentration is lower.")

	c = _experiment(
		"SD-C Supplier Reversal: Specialist vs Broad vs Matched Tools (bounded-rational)", experiment_type="theory_demonstration",
		demonstration=DEMONSTRATION_1,
		research_question="Do architectures differ in adaptation to a path-invalidating shock when actors cannot reason in language?",
		theoretical_mechanism="Only an actor that observes the inspection can learn which supplier now fails. In specialist handoff the purchasing actor never sees it.",
		architecture_a=archs["specialist"], architecture_b=archs["broad"], regime_shift=SHOCK, episode_count=12, repetitions_per_cell=5,
		actor_engine="bounded_rational", interpretation_combination="separate",
		primary_outcomes="Post-shock mean utility; performance deficit; episodes to first adaptive path.",
		notes=f"{LABEL} The third arm (broad autonomy with stage-gated tools) is compared with plain broad autonomy to isolate tool breadth.",
		factors=[
			{"factor_name": "architecture", "level_label": "specialist", "factor_type": "architecture", "architecture": archs["specialist"], "is_baseline": 1},
			{"factor_name": "architecture", "level_label": "broad", "factor_type": "architecture", "architecture": archs["broad"]},
			{"factor_name": "architecture", "level_label": "broad_matched_tools", "factor_type": "architecture", "architecture": archs["broad_matched"]},
		],
	)
	_plan("SD-C specialist vs broad: post-shock mean utility", c, "post_shock_mean_utility", "b_greater", family="SD-C")
	_plan("SD-C specialist vs broad: performance deficit", c, "performance_deficit", "a_greater", family="SD-C")
	_plan("SD-C broad vs matched-tools broad: post-shock mean utility", c, "post_shock_mean_utility", "nonzero",
		bounds="-0.02,0.02", equivalence_rule="consistent",
		question="Removing tool breadth while keeping actor continuity: no difference expected under a non-semantic engine.")

	d = _experiment(
		"SD-D Second Routine: Order-to-Cash (scripted)", experiment_type="infrastructure_validation",
		research_question="Does the same orchestrator, event store and process view run a second routine without code changes?",
		architecture_a=archs["o2c_specialist"], architecture_b=archs["o2c_broad"], episode_count=3, repetitions_per_cell=2,
		actor_engine="scripted_deterministic", notes=f"{LABEL} Scripted only.",
	)
	return {"A": a, "B": b, "C": c, "D": d}


def _label_existing_experiments():
	for name, values in {
		"Pilot P1: Specialist Handoff vs Broad Autonomy (Qwen3, stable)": {"experiment_type": "theory_demonstration", "demonstration": DEMONSTRATION_1, "actor_engine": "as_configured"},
		"Specialist vs Broad Autonomy": {"experiment_type": "infrastructure_validation"},
	}.items():
		if frappe.db.exists("EORL Experiment", name):
			frappe.db.set_value("EORL Experiment", name, values, update_modified=False)


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def _runs_for(experiment: str) -> list:
	return frappe.get_all("EORL Run", filters={"experiment": experiment}, fields=["name", "cell_id", "status"], order_by="creation asc")


def run_experiment(key: str) -> dict:
	"""Runs one of the four designs. Skips a design whose runs already
	exist so a partial session can be resumed."""
	from eorl_lab.api.experiments import launch_pilot
	from eorl_lab.runtime.orchestrator import branch_run, run_architecture

	names = {"A": "SD-A Matched Exogenous Outcomes (scripted)",
		"B": "SD-B Memory Manipulation under Supplier Reversal (bounded-rational, branched)",
		"C": "SD-C Supplier Reversal: Specialist vs Broad vs Matched Tools (bounded-rational)",
		"D": "SD-D Second Routine: Order-to-Cash (scripted)"}
	exp_name = names[key]
	if _runs_for(exp_name):
		return {"experiment": exp_name, "skipped": "runs already exist", "runs": _runs_for(exp_name)}

	if key != "B":
		result = launch_pilot(exp_name)
		frappe.db.commit()
		return result

	exp = frappe.get_doc("EORL Experiment", exp_name)
	out = []
	for rep, seed in enumerate(SEEDS):
		parent = run_architecture(exp.architecture_a, seed=seed, episode_count=6, regime_shift=SHOCK,
			actor_engine="bounded_rational", experiment=exp_name, cell_id=f"parent|rep{rep}")
		children = {}
		for label, architecture in (("memory", exp.architecture_a), ("no_memory", exp.architecture_b)):
			child = branch_run(parent["run"], 6, additional_episode_count=6, architecture_name=architecture, regime_shift=SHOCK,
				intervention_description=f"SD-B: continue after the shock with {label.replace('_', ' ')}.")
			frappe.db.set_value("EORL Run", child["branch_run"], {"experiment": exp_name, "cell_id": f"{label}|rep{rep}"})
			children[label] = child["branch_run"]
		out.append({"parent": parent["run"], **children})
		frappe.db.commit()
	return {"experiment": exp_name, "branches": out}


def _cell_runs(experiment: str, prefix: str) -> list:
	return [r.name for r in _runs_for(experiment) if (r.cell_id or "").startswith(prefix) and r.status == "completed"]


def analyze() -> dict:
	"""Applies every stored SD plan to its runs."""
	from eorl_lab.api.analysis import compare_groups, evaluate_experiment_interpretation

	a = "SD-A Matched Exogenous Outcomes (scripted)"
	b = "SD-B Memory Manipulation under Supplier Reversal (bounded-rational, branched)"
	c = "SD-C Supplier Reversal: Specialist vs Broad vs Matched Tools (bounded-rational)"
	d = "SD-D Second Routine: Order-to-Cash (scripted)"
	out = {}
	a_spec, a_broad = _cell_runs(a, "SD Specialist Handoff"), _cell_runs(a, "SD Broad Autonomy")
	for plan in ("SD-A manipulation check: actor continuity", "SD-A all-action vs consequential entropy (specialist minus broad)"):
		out[plan] = _summ(compare_groups(plan, a_spec, a_broad))
	out["SD-A matched outcomes"] = [verify_matched_outcomes(x, y) for x, y in zip(a_spec, a_broad)]

	b_mem, b_nomem = _cell_runs(b, "memory|"), _cell_runs(b, "no_memory|")
	for plan in ("SD-B memory: post-shock mean utility (paired)", "SD-B memory: post-shock path concentration (paired)"):
		out[plan] = _summ(compare_groups(plan, b_mem, b_nomem))
	from eorl_lab.api.reviewer import configuration_difference
	out["SD-B configuration difference"] = configuration_difference(b_mem[0], b_nomem[0])["differing_fields"] if b_mem else None

	c_spec = _cell_runs(c, "architecture=specialist|")
	c_broad = _cell_runs(c, "architecture=broad|")
	c_matched = _cell_runs(c, "architecture=broad_matched_tools|")
	out["SD-C specialist vs broad: post-shock mean utility"] = _summ(compare_groups("SD-C specialist vs broad: post-shock mean utility", c_spec, c_broad))
	out["SD-C specialist vs broad: performance deficit"] = _summ(compare_groups("SD-C specialist vs broad: performance deficit", c_spec, c_broad))
	out["SD-C broad vs matched-tools broad: post-shock mean utility"] = _summ(compare_groups("SD-C broad vs matched-tools broad: post-shock mean utility", c_broad, c_matched))

	out["interpretation"] = {k: evaluate_experiment_interpretation(v) for k, v in (("A", a), ("B", b), ("C", c))}
	out["SD-D runs"] = [(r.name, r.cell_id, r.status) for r in _runs_for(d)]
	frappe.db.commit()
	return out


def _summ(result: dict) -> dict:
	primary = next((r for r in result["results"] if r["test"] == result.get("primary_test")), result["results"][0])
	tost = next((r for r in result["results"] if r["test"] == "tost_equivalence"), None)
	return {
		"n": (result["n_independent_runs_a"], result["n_independent_runs_b"]), "means": (result["mean_a"], result["mean_b"]),
		"test": primary["test"], "p": primary.get("p_value"), "adjusted_p": primary.get("adjusted_p_value"),
		"g": result["standardized_effect"], "g_ci": (result["standardized_effect_ci"]["ci_low"], result["standardized_effect_ci"]["ci_high"]),
		"equivalent": tost["equivalent"] if tost else None, "interpretation": result["interpretation"]["label"],
		"results": result["analysis_result_names"],
	}


def verify_matched_outcomes(run_a: str, run_b: str) -> dict:
	"""Plan section 21's acceptance test on real runs: for each episode
	number where both runs ordered from the same supplier, the inspection
	outcome must be identical."""
	def inspections(run):
		rows = frappe.get_all("EORL Event", filters={"run": run, "event_type": "tool_result", "target_id": "inspect_received_goods"},
			fields=["episode", "payload_json"])
		numbers = dict(frappe.get_all("EORL Episode", filters={"run": run}, fields=["name", "episode_number"], as_list=True))
		out = {}
		for row in rows:
			payload = frappe.parse_json(row.payload_json)
			out[numbers[row.episode]] = (payload.get("supplier"), payload.get("quality_passed"))
		return out

	a, b = inspections(run_a), inspections(run_b)
	same_supplier = [n for n in a if n in b and a[n][0] == b[n][0]]
	matches = [n for n in same_supplier if a[n][1] == b[n][1]]
	return {"run_a": run_a, "run_b": run_b, "episodes_compared": len(same_supplier), "outcomes_identical": len(matches),
		"match_rate": (len(matches) / len(same_supplier)) if same_supplier else None}


def set_reviewer_walkthrough(pointers: dict = None) -> dict:
	"""Points the Reviewer Start Here page at specific records. Defaults
	are the language-model pilot for steps 2 to 7 and the SD runs for the
	adaptation and second-routine steps; anything not found is left for
	the page to fill with the most recent matching record."""
	pilot_arch = "Pilot Specialist Handoff (Qwen3)"
	plan = "Pilot P1: modal path share"
	result = frappe.get_all("EORL Analysis Result", filters={"analysis_plan": plan, "test_family": "welch_t"},
		fields=["name", "run_ids_group_a"], order_by="creation asc", limit_page_length=1)
	# A run that entered the registered pilot analysis, not one of the
	# smoke checks that ran on the same architecture before it.
	pilot_runs = [r.strip() for r in (result[0].run_ids_group_a or "").split(",") if r.strip()] if result else []
	result = [r.name for r in result]
	c_broad = _cell_runs("SD-C Supplier Reversal: Specialist vs Broad vs Matched Tools (bounded-rational)", "architecture=broad|")
	o2c = _cell_runs("SD-D Second Routine: Order-to-Cash (scripted)", "O2C Specialist Handoff")
	branch_parent = frappe.db.get_value("EORL Branch", {}, "parent_run", order_by="creation asc")
	defaults = {
		"architecture": pilot_arch if frappe.db.exists("EORL Architecture", pilot_arch) else None,
		"llm_run": pilot_runs[0] if pilot_runs else None,
		"process_run": pilot_runs[0] if pilot_runs else None,
		"export_run": pilot_runs[0] if pilot_runs else None,
		"branch_parent": branch_parent,
		"analysis_plan": plan if frappe.db.exists("EORL Analysis Plan", plan) else None,
		"analysis_result": result[0] if result else None,
		"adaptation_run": c_broad[0] if c_broad else None,
		"second_routine_run": o2c[0] if o2c else None,
	}
	pointers = {k: v for k, v in {**defaults, **(pointers or {})}.items() if v}
	frappe.db.set_single_value("EORL Settings", "reviewer_walkthrough_json", frappe.as_json(pointers))
	frappe.db.commit()
	return pointers
