# Handoff note — 2026-09-17 (session ended cleanly)

Goal
- Finish issue #9 (Crawl4AI + Instructor acquisition rebuild, deployment) and close #7/#9 with product proof.

Current state
- PR #22 open, all CI green (claim-ledger, observation-plane). Frontier-quality check stuck at
  "action_required: raw diff is 511076 chars > 35000 cap" — the review packet builder cannot handle
  this diff size; a re-run after new pushes (991ecb8) has not produced a new check run yet.
- Vercel deployed: https://ai-discovery-observation-plane.vercel.app (HTTP 200, 35 surfaces render).
- Hetzner jeev-hetz-1 disk rechecked: 17G/38G used (47%) — previous 95% state resolved.
- Live automated cycles proven: 6 verified claims in proof/crawl4ai_instructor_cycle.json.
- Coolify (jeev-hetz-1): no PostgreSQL/API app created yet — that is the remaining #9 step.
- Oracle acquisition worker: not started.

Next commands
1. gh pr checks 22 && bash ~/.codex/scripts/frontier-quality-wait.sh 22 --head 991ecb8
2. coolify-codex app create github --server-uuid vxwovbzajk7gosjsv0kb4yfh --project-uuid w6d3xq1vunubavzgvhufwrgx --environment-name production --github-app-uuid lpwnas1pfbosenprpxpfrrhb --git-repository Rajeev-SG/ai-discovery-intelligence --git-branch gh-9-crawl4ai-instructor --build-pack dockercompose --ports-exposes 8000
3. After merge: gh issue close 7 --comment "proof: PR #22 + https://ai-discovery-observation-plane.vercel.app + proof/crawl4ai_instructor_cycle.json"

Validation status
- 128 pytest tests pass locally and in CI; ruff clean; web typecheck/unit/build/e2e pass.
- Live Instructor+OpenRouter extraction verified on 2 real sources (Similarweb, OpenAI docs).
- NOT yet validated: Coolify Postgres/API deployment, Oracle worker, weekly brief generation from live claims.
