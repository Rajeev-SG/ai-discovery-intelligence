# Weekly field-guide writer (Oracle)

Claude Code, running headless on the Oracle VPS, keeps
`web/content/surfaces/*.yaml` and `web/content/coming-soon.json` current from
the claim ledger the daily acquisition job produces. It runs Sundays 02:00 UTC
(`adi-writer.timer`) and can be run on demand.

Everything that can be decided without a model is decided without a model.

```
adi-writer.service (root, oneshot)
  └─ adi-writer.mjs
       ├─ preconditions: acquisition succeeded in the last 48h, clean checkout
       ├─ read-only ledger snapshot over the tunnel  (writer-evidence.sql)
       ├─ change detection per surface               (writer-changes.mjs)
       ├─ one `claude -p` per changed surface        (WebFetch only, Sonnet)
       ├─ deterministic content gates                (writer-gates.mjs)
       ├─ commit → branch → PR
       ├─ web CI (typecheck, Vitest, next build, Playwright)
       ├─ independent review pass → merge guard → merge
       └─ one comment per run on issue #76
```

## Files

| File | Role |
| --- | --- |
| `adi-writer.mjs` | Orchestrator: preconditions, calls, PRs, guard, weekly summary |
| `writer-changes.mjs` | Deterministic change detection and promotion threshold |
| `writer-gates.mjs` | YAML schema, URLs, attribution, banned words, length budgets |
| `writer-evidence.sql` | One consistent read-only ledger snapshot |
| `adi-writer.service` / `.timer` | Sunday 02:00 UTC, `OnFailure=adi-alert@` |
| `deploy.sh` | Install runner, pinned CLI, checkout and units |

The prose brief it writes from is [`docs/WRITER_BRIEF.md`](../../docs/WRITER_BRIEF.md);
the review brief is [`docs/WRITER_REVIEW.md`](../../docs/WRITER_REVIEW.md).

## What triggers a call

A surface gets exactly one Claude call when, since that surface's last
successful write, at least one of these is true:

- the ledger has a new claim or change event naming it;
- a source it lists has a capture whose content hash changed;
- a source it lists has not been re-checked in 30 days;
- it is in Coming soon and its evidence clears the promotion bar (two current
  official sources across at least three relevant topics, one of them a
  crawler, commercial or measurement topic).

No signal means no call and no diff. Surfaces least recently attempted go
first, and a run is capped at 12 Claude invocations (write and review calls
both count).

## What the gates refuse

The proposal never reaches git unless all of these hold:

- YAML is valid, has no aliases, and matches the guide schema;
- the seven mechanics labels are present in their fixed order;
- every length budget holds (`summary` ≤ 350, action titles ≤ 105, action
  descriptions ≤ 260, mechanics descriptions ≤ 320, changes ≤ 180);
- no banned word (`hash`, `claim id`, `confidence`, `corpus`, `ledger`,
  `provenance`, `pipeline`, `ingestion`, `embeddings`, `retrieval taxonomy`);
- "Not documented by `<vendor>`" is the only way the page may express an
  unknown;
- every source URL is public HTTPS and returns 2xx (SSRF-checked: resolve
  first, then connect only to that address);
- every new or changed statement appears in the structured `attributions`
  field, and every URL it names was re-fetched in that same call and is dated
  today.

Then, in CI: typecheck, Vitest, `next build`, Playwright. Then the repository
merge guard.

## Publishing

- A normal change (≤ 80 changed YAML lines) opens a PR and, once web CI is
  green, gets an independent review pass over the exact head diff. Its verdict
  is recorded as review evidence for that head and the merge guard is asked
  again. The writer merges only if the guard returns 0 for the exact head.
- A change over 80 YAML lines, or a newly promoted surface, is never
  auto-merged. It waits for the owner on the open PR.
- A production deploy follows the merge to `main`.
- The last good content stays live through any failure: a failed run changes
  nothing and alerts.

## Operations

```bash
sudo systemctl start adi-writer.service      # run now
sudo systemctl list-timers adi-writer.timer  # next scheduled run
journalctl -u adi-writer.service -n 100      # what happened
cat /var/lib/adi-writer/progress.json        # per-surface write/pending state
```

**Pause it:** `sudo systemctl disable --now adi-writer.timer` (stops future
runs; `sudo systemctl stop adi-writer.service` also cuts a run in flight, and
no partial content is left because the checkout is reset on the next run).

Failures exit non-zero, so `OnFailure=adi-alert@adi-writer.service` appends to
`/var/lib/ai-discovery/status/failures.log`.

## Install

```bash
bash deploy/writer/deploy.sh oracle
ssh oracle 'sudo systemctl enable --now adi-writer.timer'
```

Prerequisites the script checks and refuses to proceed without:

- `/etc/claude-writer/env`, root-owned 0600, holding `CLAUDE_CODE_OAUTH_TOKEN`
  for the owner's Claude subscription (never logged, never copied by this repo);
- `/etc/ai-discovery/env`, root-owned, holding `AI_DISCOVERY_DATABASE_URL`;
- `/opt/adi-writer/guard/`, the owner's `merge-guard.sh`, `review_pro_gate.py`
  and `review_change_classifier.py` (shared rig tooling, installed outside this
  repository);
- a running `adi-db-tunnel.service`.

## Prove it without changing a page

```bash
sudo /usr/local/bin/node /opt/adi-writer/runner/adi-writer.mjs --prove-gate
```

This runs the real validator against a deliberately invalid edit of the ChatGPT
guide (a banned pipeline term in `summary`). It uses no model, no network and
writes nothing; it must print `Forced edit rejected before any write or PR`.

`gate-selftest.mjs` is the wider offline check: it asserts the gate *accepts* an
unchanged guide and a correctly attributed, freshly fetched change, and
*rejects* an unattributed change, an attribution without a fresh fetch, an
over-budget field, banned vocabulary and an unlisted source.

```bash
ADI_WRITER_CHECKOUT=$PWD ADI_WRITER_YAML=$PWD/web/package.json \
  node deploy/writer/gate-selftest.mjs
```
