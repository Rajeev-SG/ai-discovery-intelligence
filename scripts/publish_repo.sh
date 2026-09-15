#!/usr/bin/env bash
set -euo pipefail
repo="Rajeev-SG/ai-discovery-intelligence"

gh auth status >/dev/null
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b main
fi

git add -A
if ! git diff --cached --quiet; then
  git commit -m "Scaffold AI discovery intelligence"
fi

if gh repo view "$repo" >/dev/null 2>&1; then
  echo "Repository already exists: $repo"
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "git@github.com:${repo}.git"
  fi
else
  gh repo create "$repo" --private --description "Source-backed intelligence on how major consumer AI discovery surfaces retrieve, cite and recommend information" --source=. --remote=origin
fi

git push -u origin main
./scripts/bootstrap_issues.sh "$repo"
