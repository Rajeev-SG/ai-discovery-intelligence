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

