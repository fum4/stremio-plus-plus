#!/usr/bin/env bash
# Mac stand-in for `wt pre-merge` (devbox docs/ci.md § The pre-merge gate):
# run `mise run pre-merge` on a tree equal to the PR head, then post the result as
# the `devbox/pre-merge` commit status on that SHA. Usage: scripts/pre-merge-gate.sh [<pr>]
set -euo pipefail
pr="${1:-}"
head_sha="$(gh pr view ${pr:+"$pr"} --json headRefOid --jq .headRefOid)"
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

git fetch -q origin "$head_sha" 2>/dev/null || true
if ! git diff --quiet "$head_sha" || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "gate: working tree differs from PR head $head_sha — commit/push or stash first" >&2
  exit 1
fi

files="$(gh pr diff ${pr:+"$pr"} --name-only)"
if ! grep -qvE '(\.md$|^docs/)' <<<"$files"; then
  state=success; desc="docs-only change"
else
  start=$SECONDS
  if mise run pre-merge; then state=success; verdict=passed; else state=failure; verdict=failed; fi
  desc="pre-merge $verdict on Batman · $((SECONDS - start))s"
fi

if ! git diff --quiet "$head_sha"; then
  echo "gate: tree changed during the run — result discarded" >&2
  exit 1
fi
gh api -q .state "repos/$repo/statuses/$head_sha" \
  -f state="$state" -f context=devbox/pre-merge -f description="$desc" >/dev/null
echo "gate: devbox/pre-merge $state — $desc"
[ "$state" = success ]
