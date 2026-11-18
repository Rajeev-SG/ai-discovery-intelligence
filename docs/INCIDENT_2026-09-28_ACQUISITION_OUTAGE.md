# Incident: the daily acquisition job was dead for 51 days

**Window:** 2026-09-28 06:19 UTC → 2026-11-17 23:48 UTC
**Impact:** no new evidence entered the claim ledger. The field guide, evidence
API and weekly brief all served evidence that stopped growing on 27 September.
**Detected:** 2026-11-17, by inspection, not by alerting.
**Severity:** silent data-staleness, no data loss. Snapshots and ledger rows
written before the outage are intact and replicated.

## What happened

The daily timer fired on schedule every morning and exited about a second later.
The reason was one line in a run log:

```
Unable to find image 'adi:current' locally
docker: Error response from daemon: pull access denied for adi,
repository does not exist or may require 'docker login'
```

`adi:current` is built on the box by `deploy/oracle/deploy.sh` and has no
registry to pull from, so `docker run` failed immediately. `adi-run.sh` recorded
`ok: 0, run_exit: 125` and exited 1, which was correct. The problem was that
nothing acted on it.

Evidence, in the run logs `adi-run.sh` keeps under `/var/lib/ai-discovery/runs/`:

- last recorded success `run-2026-09-27T061211Z.log` (finished 06:17 UTC);
- first failure `run-2026-09-28T061941Z.log` (209 bytes, the message above);
- 51 consecutive 209-byte logs after it, one per day, to
  `run-2026-11-17T061754Z.log`.

## Why the image disappeared

Docker's root is `/workspace/docker` on this host. `workspace-disk-guard.service`
(`/usr/local/bin/workspace-disk-guard.sh`, installed **2026-09-27 15:12 UTC**,
nine hours after the last good run) runs every six hours and, when `/workspace`
is at or above 85% used, executes:

```bash
docker image prune -a -f
```

That removes every image with no container using it. `adi:current` is used for
about ten minutes a day and idles the other 1430, so it is exactly what the
guard is designed to reclaim. This guard is the only image-removal mechanism on
the box (checked: no cron entry, no other systemd unit, no shell history, no
repository CI step prunes images), and its install time sits inside the gap
between the last success and the first failure. Journald keeps two boots and
`/var/log/sysstat` keeps eight days, so the actual prune event is no longer on
disk; the identification is by elimination plus the timestamp, and the mechanism
is reproducible on demand.

## Why nobody noticed for 51 days

`adi-run.service` declared its failure hook in the wrong section:

```ini
[Service]
OnFailure=adi-alert@%n.service     # ignored, not [Unit]
```

systemd logged `Unknown key 'OnFailure' in section [Service], ignoring` and never
started `adi-alert@`. Three things were therefore all missing at once:

1. no alert fired on failure;
2. nothing consumed `latest.json`, which was faithfully rewritten with
   `ok: 0` every morning;
3. the daily run leaves no other trace unless you read `journalctl` or the run
   logs, which nothing did.

The status file was correct the whole time. Nothing was watching it.

## Fixes

Applied in this repository:

1. `OnFailure=` moved to `[Unit]` in `deploy/oracle/adi-run.service`, so a
   failure now starts `adi-alert@` and appends to
   `/var/lib/ai-discovery/status/failures.log`.
2. `adi-run.sh` now preflights the image with `docker image inspect`, refuses to
   pull, writes `error: image_missing` to `latest.json`, appends `IMAGE_MISSING`
   to `failures.log`, prints a specific remedy and exits 1. It also runs under
   `set -euo pipefail` and passes `--pull=never`, so a silent pull can never
   masquerade as a slow start.
3. `deploy/oracle/deploy.sh` deployed the repository at its own root instead of
   the caller's working directory. It previously computed a `SRC` variable and
   then ignored it, rsyncing `./`; run from anywhere but the repo root it
   shipped the wrong tree. It now refuses to run unless `$SRC/pyproject.toml`
   exists.

Applied to the box:

4. `adi:current` rebuilt from current `main` and `adi-run.service` rerun.

Restoration proof (Oracle, first green run since the outage):

```
/var/lib/ai-discovery/status/latest.json
{"started_at": "2026-11-18T00:04:54Z", "finished_at": "2026-11-18T00:16:19Z",
 "ok": 1, "run_exit": 0, "replicated": 1, "api_evidence_items": 137,
 "log": "/var/lib/ai-discovery/runs/run-2026-11-18T000454Z.log"}
```

`ok: 1` is the pipeline signal, `replicated: 1` is the Hetzner snapshot copy, and
`api_evidence_items` is read from the live evidence API, so it proves the whole
path rather than container exit alone. The run took 11m25s and the evidence API
grew from 135 to 137 items. Before the fix the same unit exited in under a
second with `run_exit: 125`.

## The second defect this exposed

Restoring the image exposed a separate break that had been invisible: the
pipeline gained a `mechanics_claims` asset that loads
`scripts/build_mechanics_claims.py` from the image root and re-verifies quotes
against `proof/claim_ledger/captures/`. `Dockerfile.acquisition` copied `src/`,
`config/` and `db/` but neither `scripts/` nor `proof/`, and `deploy.sh`
excluded `proof/` from the rsync. The asset therefore failed at the end of every
run, after the expensive capture and extraction work.

Both are now copied into the image. Note that the run of 27 September never
executed this asset, so it was introduced by a later commit and was never once
exercised inside the container.

## What would have caught it in minutes

- A failure hook in the right section (now in place). This is the whole fix for
  the detection half; the job was already reporting its own failure.
- A staleness check on `latest.json`: `finished_at` older than ~26 hours, or
  `ok != 1`, is a page. The writer now refuses to run unless acquisition has
  succeeded in the last 48 hours, so a repeat cannot produce fresh-looking
  prose from stale evidence, but that is a gate, not an alert.

## Residual risk

The disk guard can prune `adi:current` again the next time `/workspace` crosses
85%. That is now a loud, self-recording failure rather than a silent one, and
the remedy is a single command (`deploy/oracle/deploy.sh`). A durable fix, if
the owner wants one, is either to exclude `adi:current` from the guard (for
example a `--filter "label!=adi.keep"` on the prune plus a build label) or to
let `adi-run.sh` rebuild the image when it is missing. Neither is in this
change: the first edits shared box tooling outside this repository, and the
second trades a loud failure for an unattended build during the 06:10 window.
Both are recorded here as open decisions.
