"""Writes artifact_manifest.json at the repository root (submission-day
plan section 17): a machine-readable description of what this commit
implements. Run from anywhere with plain Python 3; it reads the
repository and git, not a Frappe site.

    python3 scripts/generate_artifact_manifest.py [--tests-passing N] [--tests-run-log PATH]

The test count is counted from the test files. The passing count is
taken from --tests-passing or parsed from a saved `bench run-tests` log
("Ran N tests ... OK"); it is null if neither is given, never assumed.
"""
import argparse
import ast
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "eorl_lab")


def git(*args):
	try:
		return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip() or None
	except Exception:
		return None


def count_tests():
	files, total = {}, 0
	for dirpath, _dirs, names in os.walk(PKG):
		for name in names:
			if name.startswith("test_") and name.endswith(".py"):
				path = os.path.join(dirpath, name)
				tree = ast.parse(open(path).read())
				n = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
				files[os.path.relpath(path, ROOT)] = n
				total += n
	return total, dict(sorted(files.items()))


def doctypes():
	base = os.path.join(PKG, "eorl_lab", "doctype")
	out = []
	for d in sorted(os.listdir(base)):
		path = os.path.join(base, d, f"{d}.json")
		if os.path.exists(path):
			out.append(json.load(open(path))["name"])
	return out


def pages():
	base = os.path.join(PKG, "eorl_lab", "page")
	return sorted(json.load(open(os.path.join(base, d, f"{d}.json")))["name"] for d in os.listdir(base)
		if os.path.exists(os.path.join(base, d, f"{d}.json")))


def whitelisted():
	out = []
	base = os.path.join(PKG, "api")
	for name in sorted(os.listdir(base)):
		if not name.endswith(".py"):
			continue
		tree = ast.parse(open(os.path.join(base, name)).read())
		for node in tree.body:
			if isinstance(node, ast.FunctionDef) and any("whitelist" in ast.unparse(d) for d in node.decorator_list):
				out.append(f"eorl_lab.api.{name[:-3]}.{node.name}")
	return out


IMPLEMENTED = [
	"configurable organizational architectures (specialist handoff, broad autonomy, broad autonomy with stage-gated matched tools)",
	"routine templates: Procure-to-Pay and Order-to-Cash through one orchestrator",
	"authority firewall outside the model (tool policies, submit and message rights, write budgets, hard and soft rules)",
	"persistent actors with episodic, recent, semantic and procedural memory backends",
	"communication policies checked on agent-chosen messages",
	"actor engines chosen independently of architecture: scripted_deterministic, bounded_rational, llm (OpenAI-compatible)",
	"seeded scenario generation with case hashes and an exogenous/endogenous state partition",
	"matched exogenous outcome model (identical action, identical outcome across architectures)",
	"path-invalidating supplier-quality reversal",
	"counterfactual branching with memory cloning",
	"append-only event store with payload hashes",
	"registered sequence views (all, consequential, write, actor-function actions)",
	"process metrics: sequence variety, concentration, continuity, attribute-level path coherence v1",
	"adaptive repertoire v2 (observed / viable / activated-after-shock) and shock-adaptation measures",
	"construct registry with executable measurement functions",
	"analysis plans with independence guardrail, paired-branch verification, Welch and permutation tests, Hedges g with bootstrap CI, TOST, mixed effects, multiplicity correction, structured interpretation rules",
	"seeded power planning for independent and paired designs",
	"QAP network comparison and Kaplan-Meier time to recovery",
	"reproducibility bundles and scripted run reproduction",
	"queued background execution with cancellation",
	"run failure taxonomy and per-call model telemetry",
	"read-only reviewer role, reviewer walkthrough and evaluation matrix pages",
]
PARTIAL = [
	"decision and assignment rights are recorded and measured but not enforced",
	"model-driven runs are reproducible in configuration, scenario stream and trace, not bit for bit",
	"branches share one ERP company, so ERP aggregates are not comparable across branches",
	"one language-model family (Qwen3 27B) has been exercised",
	"attribute-level path coherence is an EORL operationalization, not verified line by line against the cited estimator",
]
PLANNED = [
	"second language-model family robustness runs",
	"shared and vector memory backends; anthropic provider",
	"graphical Agent Studio, Architecture Designer and Scenario Studio",
	"distributed workers and per-branch ERP isolation",
	"temporal motif analysis and sequence-distance clustering",
	"full-scale registered study of propositions P1 to P3",
]


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--tests-passing", type=int)
	parser.add_argument("--tests-run-log")
	parser.add_argument("--release-tag", default="orgsci-stage1-2026-11-01")
	args = parser.parse_args()

	total, by_file = count_tests()
	passing, ran = args.tests_passing, None
	if args.tests_run_log and os.path.exists(args.tests_run_log):
		log = open(args.tests_run_log).read()
		m = re.search(r"Ran (\d+) tests? in", log)
		if m:
			ran = int(m.group(1))
			if re.search(r"^OK", log, re.M) and passing is None:
				passing = ran

	manifest = {
		"name": "Executable Organizational Routine Laboratory",
		"short_name": "EORL",
		"version": "0.1-stage1",
		"release_tag": args.release_tag,
		# The code this manifest describes. When the manifest is committed on
		# its own afterwards (scripts/freeze_release.sh), the release tag
		# points to that next commit, whose only change is this file.
		"commit": git("rev-parse", "HEAD"),
		"commit_date": git("show", "-s", "--format=%cI", "HEAD"),
		"working_tree_clean": git("status", "--porcelain") in (None, ""),
		"submission_date": "2026-11-01",
		"platform": "Frappe 14 / ERPNext 14 (Python 3.10)",
		"primary_contribution": "Reusable research infrastructure for executable organizational theory",
		"implemented_capabilities": IMPLEMENTED,
		"partial_capabilities": PARTIAL,
		"planned_capabilities": PLANNED,
		"tests": {"count": total, "passing": passing, "ran": ran, "by_file": by_file},
		"doctypes": doctypes(),
		"pages": pages(),
		"whitelisted_api": whitelisted(),
		"routine_templates": ["Procure-to-Pay", "Order-to-Cash"],
		"actor_engines": ["scripted_deterministic", "bounded_rational", "llm"],
		"demonstrations": [{
			"id": "agentic_routinization",
			"title": "Demonstration 1: Agentic Routinization and Adaptive Repertoire",
			"status": "demonstration / proof of capability; not a test of the theory",
		}],
	}
	path = os.path.join(ROOT, "artifact_manifest.json")
	with open(path, "w") as fh:
		json.dump(manifest, fh, indent=1)
		fh.write("\n")
	print(f"wrote {path}: {total} tests counted, passing={passing}, commit={manifest['commit']}")


if __name__ == "__main__":
	main()
