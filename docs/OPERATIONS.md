# Operations

## Health signals

Track:

- source fetch success/failure and status code;
- extraction completeness;
- changedetection watch health;
- feed staleness;
- claims produced per source;
- evidence without methodology metadata;
- surfaces with no recent verification;
- source concentration by claim;
- unresolved contradictions;
- weekly brief item count;
- pipeline runtime/failures.

## Existing observability

Use Dagster's run/asset UI and integrate with the user's existing Grafana/OTEL stack where useful. Do not create a bespoke monitoring dashboard before these are insufficient.

## Failure philosophy

A failed source must become visible in source health and should not silently freeze an old claim as “current”. Old claims need `last_verified` and staleness rules.

A scheduled unit that fails must alert, and a unit that stops running must be
visible without reading logs. `adi-run.service` carries
`OnFailure=adi-alert@%n.service` in its `[Unit]` section; putting that key in
`[Service]` makes systemd ignore it silently, which is how the acquisition job
failed for 51 days in 2026 (see
[`INCIDENT_2026-09-28_ACQUISITION_OUTAGE.md`](INCIDENT_2026-09-28_ACQUISITION_OUTAGE.md)).

## Production web deploy

`web/` is a Next.js app built with `BASE_PATH=/solutions/ai-discovery` and served
at <https://rajeevg.com/solutions/ai-discovery>. rajeevg.com proxies the Vercel
project `ai-discovery-observation-plane` (team `rajeevgills-projects`, project
`prj_mNOpPbulq27ufNfs6k1QJl7Ic17G`, stable alias `discovery.rajeevg.com`).

The deploy path is the repository, not anyone's laptop:

- The Vercel project is git-connected to
  `Rajeev-SG/ai-discovery-intelligence` with production branch `main`, **root
  directory `web`** and framework Next.js. Build and install commands still come
  from `web/vercel.json`.
- Every push to `main` builds and promotes a production deployment with no
  manual step. A content-only change under `web/content/**` is enough — that is
  how the weekly writer's merges reach readers.
- `BASE_PATH` and `EVIDENCE_API_URL` are project environment variables scoped to
  production, so preview builds (pull requests) render without the base path and
  without the live evidence API by design.

That connection is the whole point: merging a content PR from the writer *is*
the deploy. Until 2026-11-18 the project had no git connection, so merging a
writer PR published nothing — production only moved when someone ran
`vercel deploy` by hand. If a merge to `main` does not produce a production
deployment carrying that commit, the deploy path is broken, and the run is not
publishing.

Verify instead of assuming:

```bash
gh api repos/Rajeev-SG/ai-discovery-intelligence/commits/main --jq .sha
curl -sI https://rajeevg.com/solutions/ai-discovery/surfaces/chatgpt   # expect 200
```

Then open the project's Deployments: the top production entry must be `READY`,
sourced from `git`, carrying that commit.

Rollback: `vercel rollback <previous-production-url> --scope rajeevgills-projects`,
or revert the commit on `main` — the revert is itself a deployment.

Fallback, only if the git connection is broken: from `web/`,
`vercel --prod --scope rajeevgills-projects`. The project-scoped token in
`~/.vercel-rajeevgills.token` authorises that and **expires 2026-12-18**; renew
it before then if the fallback still matters. A manual deploy carries no commit
reference, which is why it cannot be the durable answer.

## Oracle schedules

| Timer | When | What | Pause |
| --- | --- | --- | --- |
| `adi-run.timer` | weekly, Sat 06:10 UTC (on demand: `sudo intel-refresh adi`) | capture → extract → claim ledger → snapshot replication | `systemctl disable --now adi-run.timer` |
| `adi-writer.timer` | Sundays 02:00 UTC | field-guide updates from new evidence | `systemctl disable --now adi-writer.timer` |

The writer refuses to run unless acquisition has succeeded in the last 48 hours,
so a pipeline outage cannot be covered up by fresh-looking prose. It reports one
comment per run on
[Weekly content updates](https://github.com/Rajeev-SG/ai-discovery-intelligence/issues/76);
a run with nothing to do still comments `No changes.`, so silence means the unit
did not run.

```bash
sudo systemctl start adi-writer.service       # run now
journalctl -u adi-writer.service -n 100       # what happened
cat /var/lib/adi-writer/progress.json         # per-surface state
tail /var/lib/ai-discovery/status/failures.log # every OnFailure marker
```

