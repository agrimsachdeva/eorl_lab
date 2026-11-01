#!/bin/bash
# Freeze the Stage 1 release (submission-day plan section 33).
# Run on the host, from the repository root, after reviewing and
# committing the build:
#
#   scripts/freeze_release.sh /path/to/run-tests.log
#
# It refuses to run on a dirty tree, writes artifact_manifest.json for
# the current commit (test count from the files, passing count from the
# log), commits that one file, and creates the annotated tag. It does not
# push; push the branch and tag yourself when ready.
set -euo pipefail
TAG=orgsci-stage1-2026-11-01
LOG=${1:?usage: scripts/freeze_release.sh <bench run-tests log>}

cd "$(dirname "$0")/.."
if [ -n "$(git status --porcelain)" ]; then
	echo "working tree is not clean; commit or stash first" >&2
	exit 1
fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
	echo "tag $TAG already exists" >&2
	exit 1
fi

CODE_COMMIT=$(git rev-parse HEAD)
python3 scripts/generate_artifact_manifest.py --tests-run-log "$LOG" --release-tag "$TAG"
git add artifact_manifest.json
git commit -m "Artifact manifest for $TAG (describes $CODE_COMMIT)"
git tag -a "$TAG" -m "Organization Science Stage 1 submission, 2026-11-01. Code commit $CODE_COMMIT."
echo "tagged $TAG at $(git rev-parse HEAD); manifest describes code commit $CODE_COMMIT"
echo "next: git push upstream main && git push upstream $TAG"
