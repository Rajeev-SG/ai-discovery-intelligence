#!/usr/bin/env bash
set -euo pipefail
repo="${1:-Rajeev-SG/ai-discovery-intelligence}"
for body in .github/issue-seeds/[0-9][0-9]-*.md; do
  title=$(sed -n '1s/^# //p' "$body")
  if [[ -z "$title" ]]; then
    echo "Missing title in $body" >&2; exit 1
  fi
  if gh issue list --repo "$repo" --state all --limit 200 --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "exists: $title"
    continue
  fi
  gh issue create --repo "$repo" --title "$title" --body-file "$body"
done
