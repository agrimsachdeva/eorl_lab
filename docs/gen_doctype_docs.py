"""Generates docs/doctypes/*.md from the actual EORL Lab DocType JSON
definitions, so the DocType reference documents real, current fields
rather than hand-maintained prose that drifts from the schema.

Run from the repo root whenever a DocType's fields change:

    python3 docs/gen_doctype_docs.py
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR = REPO_ROOT / "eorl_lab" / "eorl_lab" / "doctype"
OUT_DIR = Path(__file__).resolve().parent / "doctypes"

# Grouped for the generated index's reading order -- roughly
# environment/organization/actors/process/science, matching the V2
# spec's own five-layer model (see docs/guide/core-concepts.md).
GROUPS = {
	"Organization & Authority": [
		"eorl_tool", "eorl_tool_policy", "eorl_allowed_tool", "eorl_communication_policy",
		"eorl_communication_edge", "eorl_task_assignment", "eorl_process_grammar",
		"eorl_process_stage", "eorl_process_transition",
	],
	"Actors": [
		"eorl_agent_template", "eorl_model_profile", "eorl_memory_profile", "eorl_memory_record",
	],
	"Architecture & Environment": [
		"eorl_architecture", "eorl_architecture_actor_slot", "eorl_regime_shift",
	],
	"Runs, Episodes & Branching": [
		"eorl_run", "eorl_episode", "eorl_branch", "eorl_event",
	],
	"Science: Experiments & Constructs": [
		"eorl_experiment", "eorl_experiment_factor", "eorl_construct",
		"eorl_analysis_plan", "eorl_analysis_result",
	],
}


def load_doctype(folder: Path):
	json_path = folder / f"{folder.name}.json"
	if not json_path.exists():
		return None
	return json.loads(json_path.read_text())


def render_doctype_md(doc: dict) -> str:
	name = doc["name"]
	lines = [f"# {name}", ""]
	if doc.get("istable"):
		lines.append("*Child table.*")
		lines.append("")

	fields_by_name = {f["fieldname"]: f for f in doc.get("fields", [])}
	lines.append("| Field | Type | Description |")
	lines.append("|---|---|---|")
	for fieldname in doc.get("field_order", []):
		field = fields_by_name.get(fieldname)
		if not field:
			continue
		if field["fieldtype"] in ("Section Break", "Column Break"):
			continue
		label = field.get("label", fieldname)
		fieldtype = field["fieldtype"]
		if field.get("options") and fieldtype in ("Link", "Table"):
			fieldtype = f"{fieldtype} → `{field['options']}`"
		elif field.get("options") and fieldtype == "Select":
			opts = " / ".join(field["options"].split("\n"))
			fieldtype = f"Select ({opts})"
		description = (field.get("description") or "").replace("\n", " ")
		lines.append(f"| `{fieldname}` ({label}) | {fieldtype} | {description} |")
	lines.append("")
	return "\n".join(lines)


def main():
	OUT_DIR.mkdir(parents=True, exist_ok=True)
	all_doctype_folders = sorted(p for p in MODULE_DIR.iterdir() if p.is_dir())
	grouped_folder_names = {f for names in GROUPS.values() for f in names}

	index_lines = ["# DocType Reference", "", (
		"Generated directly from each DocType's JSON definition "
		"(`docs/gen_doctype_docs.py`) -- this always reflects the actual "
		"current schema, not a hand-written description that can drift "
		"from it. Grouped roughly by the V2 spec's five-layer model "
		"(see [Core Concepts](../guide/core-concepts.md))."
	), ""]

	for group_name, folder_names in GROUPS.items():
		index_lines.append(f"## {group_name}")
		index_lines.append("")
		for folder_name in folder_names:
			folder = MODULE_DIR / folder_name
			if not folder.is_dir():
				continue
			doc = load_doctype(folder)
			if not doc:
				continue
			out_path = OUT_DIR / f"{folder_name}.md"
			out_path.write_text(render_doctype_md(doc))
			index_lines.append(f"- [{doc['name']}]({folder_name}.md)")
		index_lines.append("")

	ungrouped = [f for f in all_doctype_folders if f.name not in grouped_folder_names]
	if ungrouped:
		index_lines.append("## Other")
		index_lines.append("")
		for folder in ungrouped:
			doc = load_doctype(folder)
			if not doc:
				continue
			out_path = OUT_DIR / f"{folder.name}.md"
			out_path.write_text(render_doctype_md(doc))
			index_lines.append(f"- [{doc['name']}]({folder.name}.md)")
		index_lines.append("")

	(OUT_DIR / "index.md").write_text("\n".join(index_lines))
	print(f"Wrote {len(list(OUT_DIR.glob('*.md')))} DocType pages to {OUT_DIR}")


if __name__ == "__main__":
	main()
