# Handoff note — 2026-09-18 (synced)

Goal
- Finish PR #22 on branch `gh-9-crawl4ai-instructor`, then close #7/#9 only when their acceptance criteria are genuinely satisfied.
- Do not trust a head SHA embedded in this file: this handoff itself changes the branch head. Resolve the current PR head with `gh pr view 22 --repo Rajeev-SG/ai-discovery-intelligence --json headRefOid -q .headRefOid` before any wait/check command.
- CI (`claim-ledger-ci`, `web-ci`) is green. The remaining merge blocker is `frontier-quality`.

## Frontier-quality blocker

The OpenReview/Vercel gate accepts the enqueue but the workflow has not been executing:
- label/webhook trigger returns `{"ok":true,"queued":true}`;
- no fresh workflow runtime logs;
- no Redis idempotency key for the new run;
- no fresh check-run update;
- the stale visible result is the earlier packet-size `action_required` refusal.

Already fixed/verified:
- Vercel env values were re-added without literal quote characters.
- `FRONTIER_MAX_DIFF_CHARS=150000`.
- `FRONTIER_MAX_PACKET_CHARS=160000`.
- Local packet build is safe at ~153k chars.
- Local engine reaches budget reservation successfully.
- Current CI is green.

Next:
1. Check Vercel → `openreview-openrouter` → AI/Workflows for stuck/failed workflow executions.
2. If redeploy-based deployments are the problem, run a genuine `vercel deploy --prod` from `/Users/rajeev/Code/openreview`.
3. Re-trigger:
   `gh pr edit 22 --repo Rajeev-SG/ai-discovery-intelligence --remove-label frontier-review --add-label frontier-review`
4. Resolve the current head dynamically, then wait:
   `HEAD=$(gh pr view 22 --repo Rajeev-SG/ai-discovery-intelligence --json headRefOid -q .headRefOid)`
   `~/.codex/scripts/frontier-quality-wait.sh 22 --repo Rajeev-SG/ai-discovery-intelligence --head "$HEAD" --timeout 600`
5. If PASS, run merge guard and squash-merge. Do not bypass the gate merely because infrastructure was previously stuck.

## #9 closure gate — deployment proof still required

Do not close #9 just because PR #22 merges. Before closure, prove all of the following:

- **Evidence API actually runs as a service.** The current Compose/Coolify deployment was effectively DB-only; add/containerise the FastAPI `api` service and verify it is reachable.
- **Observation plane is live** at the Vercel deployment and reads real evidence.
- **End-to-end refresh proof:** trigger at least one real source refresh through acquisition → snapshot → Instructor extraction → validated evidence/claim output, and document the resulting record/change.
- **PostgreSQL backup + restore** is exercised and documented.
- **Oracle acquisition role is deployed/verified**, not merely represented in code/config.
- No durable unique state exists only on Oracle.
- Do not touch or repurpose any `ad-platform-intelligence` resource on the shared Coolify host.

Current known resources/evidence:
- observation plane: https://ai-discovery-observation-plane.vercel.app
- `proof/crawl4ai_instructor_cycle.json`
- `proof/brief/brief.json`
- Coolify Postgres: `zfq4ssyudky0qtjnjefhnuk2`
- Coolify compose app: `iyercyduhzplx2m7ldqqz0cp`

## #7 closure gate

Close #7 only after its issue acceptance proof is present: a real evidence change updates exactly one POV proposition with before/after + changelog, and at least one current event is shown not to alter the POV.

## Gotchas

- `coolify-codex` CLI token is read-only; writes use the root token or server-side tinker.
- Do not touch `ad-platform-intelligence` resources on the shared Coolify host.
- `.env.local` in `/Users/rajeev/Code/openreview` may contain regenerated `[SENSITIVE]` placeholders; do not use it as a secret-value source.
- The frontier PR lifecycle key can retain `needs_manual_review`; clear only the PR-specific Redis key if a genuine clean retry is required.
