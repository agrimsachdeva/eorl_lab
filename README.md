# EORL: Executable Organizational Routine Laboratory

**What it is.** EORL is research infrastructure for organizational theory. A theory's
constructs are written down as an executable organization (roles, authority, memory,
communication and a routine running on a real ERP system), acted on by computational
actors, branched into counterfactual histories, recorded as an append-only process trace
and analyzed with design-aware inference.

**Why it exists.** Organizational theories make claims about structures that cannot be
varied in the field while holding everything else fixed. EORL makes the structure the
manipulated variable: the same scenario stream, the same tools and the same actors can be
run under a different architecture, memory or regime, and every action is observable.

**What is implemented.** A Frappe/ERPNext application with configurable architectures, two
routine templates (procure-to-pay and order-to-cash), an authority firewall outside the
model, five memory backends, three actor engines (scripted, bounded-rational, language
model), counterfactual branching, a Construct Registry with executable measures, and an
analysis layer with registered plans, an independence guardrail, effect-size intervals,
equivalence tests, multiplicity correction and structured interpretation rules. The full
list, with what is partial and what is planned, is in
[`artifact_manifest.json`](artifact_manifest.json) and [LIMITATIONS.md](LIMITATIONS.md).

**How to run it.** See [QUICKSTART.md](QUICKSTART.md): install the app on a Frappe 14 /
ERPNext 14 bench, run the tests, run a scripted episode.

**How to verify the submission.** Log in to the demonstration site with the reviewer
account given in the submission form and open **`/app/eorl-reviewer`**, a five-minute
guided walkthrough of eleven real records. [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) is the
same walkthrough on paper, with the evaluation matrix.

**The first demonstration.** *Demonstration 1: Agentic Routinization and Adaptive
Repertoire* compares specialist handoff with broad autonomy, with and without memory,
before and after a supplier-quality reversal that makes the previously best path the
worse one. Its runs so far demonstrate the instrument. They are not a test of the theory.

## Documents

| Document | For |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | Installing, testing and running a first episode |
| [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) | Verifying the artifact in about five minutes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the code is organized and where each capability lives |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | What is reproducible, how, and to what degree |
| [LIMITATIONS.md](LIMITATIONS.md) | What the artifact does not do |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [CITATION.cff](CITATION.cff) | How to cite |
| [PROGRESS.md](PROGRESS.md) | The full build record, milestone by milestone |
| `docs/` | The researcher guidebook and API reference (MkDocs site) |

## Release

The Stage 1 submission refers to the tag `orgsci-stage1-2026-11-01`. The commit it points
to is recorded in `artifact_manifest.json`, on the reviewer page and in every run manifest
(`code_commit_at_launch`).

## License

MIT. See [LICENSE](LICENSE).
