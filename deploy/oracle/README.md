# Oracle acquisition worker deployment (issue #9)

The acquisition pipeline (**Dagster → Crawl4AI → private snapshot store →
Instructor/Pydantic via OpenRouter**) runs unattended on the Oracle VPS as a
Docker container driven by a systemd timer, mirroring the proven
ad-platform-intelligence pattern. The durable evidence Postgres stays on the
Hetzner/Coolify host; Oracle owns no unique durable state.

## Layout on the host

| Path | Purpose |
| --- | --- |
| `/opt/ai-discovery/app` | rsynced source tree, build context for `adi:current` |
| `/var/lib/ai-discovery/snapshots` | private hash-addressed snapshot store (replicated to Hetzner after each run) |
| `/var/lib/ai-discovery/dagster-home` | Dagster run history (operational, not product state) |
| `/var/lib/ai-discovery/status/latest.json` | health signal written every run (includes the live API's evidence count) |
| `/var/lib/ai-discovery/status/failures.log` | appended by `OnFailure=adi-alert@` |
| `/var/lib/ai-discovery/runs/*.log` | per-run container output |
| `/etc/ai-discovery/env` | `OPENROUTER_API_KEY`, `AI_DISCOVERY_DATABASE_URL`, `AI_DISCOVERY_SNAPSHOT_DIR=/data/snapshots`, `DAGSTER_HOME=/data/dagster-home`; mode 600, never in Git |
| `/etc/ai-discovery/db-tunnel-key` | SSH key restricted on Hetzner to a single TCP forward |
| `/etc/ai-discovery/replica-key` | SSH key restricted on Hetzner for snapshot rsync only |
| `/etc/systemd/system/adi-run.{service,timer}`, `adi-alert@.service`, `adi-db-tunnel.service` | schedule + tunnel + alert |

## One-time manual setup (credentials/keys — by hand, never in a script)

1. Env file on Oracle: `ssh oracle 'sudoedit /etc/ai-discovery/env && chmod 600 /etc/ai-discovery/env'`
2. Tunnel key: `ssh oracle 'ssh-keygen -t ed25519 -f /etc/ai-discovery/db-tunnel-key -N "" -C adi-db-tunnel'`
   then append its public key to Hetzner `authorized_keys` with options:
   `from="100.112.158.79",command="echo tunnel-only",no-pty,no-agent-forwarding,no-X11-forwarding,permitopen="127.0.0.1:55432"`
3. Replica key: `ssh oracle 'ssh-keygen -t ed25519 -f /etc/ai-discovery/replica-key -N "" -C adi-replica'`
   then append its public key to Hetzner `authorized_keys` with options:
   `from="100.112.158.79",command="rrsync /var/lib/ai-discovery",no-pty,no-agent-forwarding,no-X11-forwarding`
   (fall back to `from=` + `no-pty` only if `rrsync` is not installed).
4. Enable: `ssh oracle 'systemctl enable --now adi-db-tunnel && systemctl enable --now adi-run.timer'`

## Deploy

```bash
deploy/oracle/deploy.sh            # rsync + docker build + install units
```

## Health check

```bash
ssh oracle 'cat /var/lib/ai-discovery/status/latest.json'
ssh oracle 'cat /var/lib/ai-discovery/status/failures.log'
ssh oracle 'systemctl list-timers adi-run.timer'
```

A fresh `latest.json` with `ok: true`, `replicated: 1` and a recent
`finished_at` is the "pipeline ran, produced evidence, and no state is
Oracle-only" signal. `api_evidence_items` is read from the live evidence API,
so it proves the end-to-end path (capture → extraction → ledger → API), not
just container health.
