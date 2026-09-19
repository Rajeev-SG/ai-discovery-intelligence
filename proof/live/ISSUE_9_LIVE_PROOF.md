# Issue #9 — live operational proof

Attached evidence for closing #9. Everything below was run against the real
production split (Oracle acquisition VPS → Hetzner/Coolify durable Postgres +
evidence API → Vercel observation plane), not mocks or fixtures.

## Architecture proven end to end

`Dagster → Crawl4AI → private snapshots → Instructor/Pydantic via OpenRouter →
validated claim → change event → evidence API → observation plane`

## 1. Oracle acquisition worker kit deployed (PR #42 + this branch)

- `deploy/oracle/deploy.sh` installed `adi:current` (Dagster + Crawl4AI +
  Chromium + Instructor) and the systemd units.
- `adi-db-tunnel.service` active; `127.0.0.1:55432` forwarded to the
  loopback-only Hetzner Postgres publish.
- `adi-run.timer` enabled; next fire `2026-09-20 06:13:29 UTC`.

```
$ systemctl is-enabled adi-run.timer adi-db-tunnel   # enabled / enabled
$ systemctl is-active  adi-db-tunnel                 # active
$ systemctl list-timers adi-run.timer
NEXT                         LEFT  UNIT          ACTIVATES
Sun 2026-09-20 06:13:29 UTC  14h   adi-run.timer adi-run.service
```

Two real deployment bugs were found and fixed on this branch (both were
blocking the unattended run):

1. **Tailscale SSH on the tailnet IP.** Hetzner runs Tailscale SSH, which
   intercepts `:22` on `100.109.237.19` and demands interactive browser auth, so
   the restricted key could never authenticate for an unattended systemd tunnel
   or `rrsync`. The kit now connects over Hetzner's public IP `89.167.5.185`
   (plain sshd, key auth). The restricted `authorized_keys` entries are now
   `from="100.112.158.79,140.238.91.73"` (tailnet + Oracle egress) with
   `permitopen="127.0.0.1:55432"` / `rrsync`, so the DB port stays
   loopback-only and never public.
2. **rrsync target path.** `rrsync` roots at `/var/lib/ai-discovery`, so the
   replication target is `snapshots/` (relative), not the absolute path.

## 2. Real production refresh, end to end

Run: `run-2026-09-19T151109Z.log` (systemd `adi-run.service`), `RUN_SUCCESS`.

```
$ cat /var/lib/ai-discovery/status/latest.json
{"started_at": "2026-09-19T15:11:09Z", "finished_at": "2026-09-19T15:16:43Z",
 "ok": 1, "run_exit": 0, "replicated": 1, "api_evidence_items": 12,
 "log": "/var/lib/ai-discovery/runs/run-2026-09-19T151109Z.log"}
```

Durable Hetzner ledger after the run:

```
source           51
evidence_item    12
claim             1
change_event      1
```

## 3. Live observation plane shows real production evidence

`/health` from the live API:

```json
{"status":"degraded","evidence_items":12,"sources":51,"sources_not_ok":39,"discovered_candidates":18}
```

`/surface-evidence` (chatgpt surface is `evidenced`, not empty state):

```json
{"count":1,"surfaces":{"chatgpt":{"surface":"chatgpt","evidence_state":"evidenced",
 "claims":[{"claim_id":"0b187a5b6f942c1d2a3fcb12285238e5","topic":"crawler_index_policy",
 "statement":"It can take approximately 24 hours for OpenAI's systems to adjust for
 search results after a site's robots.txt update.","surfaces":["chatgpt"], ...}],
 "latest_change":{... "event_type":"crawler_policy" ...}}}}
```

The deployed plane (https://ai-discovery-observation-plane.vercel.app, root
`web/`, `EVIDENCE_API_URL` set in Production) renders that claim: fetching the
page HTML contains the claim statement and the `evidenced` state, the rest of
the registry still shows explicit no-evidence.

## 4. Change event linked to the claim

`/events`:

```json
{"count":1,"items":[{"id":"0b187a5b6f94","event_type":"crawler_policy",
 "title":"It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update.",
 "surfaces":["chatgpt"],"claims":["0b187a5b6f942c1d2a3fcb12285238e5"],
 "evidence_urls":["https://developers.openai.com/api/docs/bots"],
 "observed_at":"2026-09-19T15:16:37.517117+00:00",
 "source_hash":"b44ccba0e839d9e767231a7d3ac1cfe930209d60ea46fafec1a8e3e9168664aa"}]}
```

## 5. Snapshot replication — no unique durable state is Oracle-only

Oracle owns only the private snapshot store, and it is byte-identical on
Hetzner after every successful run:

```
Oracle : 35 files, manifest sha256 a60bc2ab1f5ce372279f6732b49eabcd0177d683d38a8146d5871fa367e7e030
Hetzner: 35 files, manifest sha256 a60bc2ab1f5ce372279f6732b49eabcd0177d683d38a8146d5871fa367e7e030
```

Every durable *product* row (claims, evidence, events) lives in the Hetzner
Postgres; Oracle keeps only operational run history (`dagster-home`, `runs`,
`status`), which is not product state. Product data therefore survives Oracle
loss: the plane reads the Hetzner API, and the snapshots are already replicated.

## 6. Isolation from ad-platform-intelligence

Shared Coolify/Oracle host, fully separate resources:

```
adi  containers: api-iyercyduhzplx2m7ldqqz0cp-*, db-iyercyduhzplx2m7ldqqz0cp-*  (project iyercyduhzplx2m7ldqqz0cp)
adpi containers: adpi-corpus-db
adi  volume    : iyercyduhzplx2m7ldqqz0cp_ai-discovery-intelligence-db
adpi volume    : adpi-corpus-data
```

Separate project prefix, separate DB/volume, separate Oracle host, separate
Postgres (`55432` for ai-discovery vs `55433` for adpi), separate restricted
keys. Neither the evidence DB nor the corpus DB is publicly reachable
(`89.167.5.185:55432` times out).

## Fixes this branch carried (both required for the live proof)

1. `claim_pipeline.py` called `claims_from_extraction` with the default
   `human_reviewed=False`, so the ledger provenance guard rejected every
   `llm_proposal` claim and the lane persisted 0 claims in production. The fix
   adds a distinct `verified_against_capture` provenance flag: the unattended lane
   asserts that every declared locator was deterministically checked against the
   capture bytes — the honest property it establishes — and never asserts
   `human_reviewed`, which would falsely claim a person read the model output.
   Both flags are persisted and surfaced in the API.
2. No production code derived change events from claims (PR #41 removed the
   only generator), so `/events` was permanently empty. Added
   `change_derivation.py` (deterministic, model-free topic→event mapping) and
   wired it into the claims lane.

Integrity preserved: 178 tests pass, ruff clean, scorecard 8/8.
