# Oracle acquisition worker deployment (issue #9)

The acquisition pipeline (**Dagster → Crawl4AI → private snapshot store →
Instructor/Pydantic via OpenRouter**) runs unattended on the Oracle VPS as a
Docker container driven by a systemd timer, mirroring the proven
ad-platform-intelligence pattern. The durable evidence Postgres stays on the
Hetzner/Coolify host; Oracle owns no unique durable state.

Oracle reaches Hetzner over the **tailnet**, never the public internet. The
default `:22` on Hetzner is served by Tailscale SSH, which requires interactive
browser auth and so cannot be used by an unattended timer. A second sshd listener
is bound to the Tailscale interface only (`ssh.socket.d/60-adi-tunnel.conf`,
`/etc/ssh/sshd_config.d/60-adi-tunnel.conf`) on port `2222`; it is real sshd, so
per-key restrictions apply and it refuses root.

Both restricted keys belong to a dedicated **non-root** `adi-worker` account on
Hetzner:

- tunnel key — `from="<tailnet>,<oracle-egress>",command="/bin/false",no-pty,
  no-agent-forwarding,no-X11-forwarding,permitopen="127.0.0.1:55432"`
- replica key — `from="<tailnet>,<oracle-egress>",command="/usr/bin/rrsync
  /var/lib/ai-discovery/snapshots",no-pty,no-agent-forwarding,no-X11-forwarding`

The Postgres publish stays loopback-only on Hetzner (`127.0.0.1:55432`); the
tunnel key can open only that one forward, so the database is never exposed
publicly. Oracle no longer needs, and no longer holds, a root key on Hetzner.

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
   `from="100.112.158.79,140.238.91.73",command="/bin/false",no-pty,no-agent-forwarding,no-X11-forwarding,permitopen="127.0.0.1:55432"`
   into `/var/lib/adi-worker/.ssh/authorized_keys` (owner `adi-worker`). The
   tailnet IP is the traffic source; keep the Oracle public egress IP so a
   public-IP fallback still authenticates.
3. Replica key: `ssh oracle 'ssh-keygen -t ed25519 -f /etc/ai-discovery/replica-key -N "" -C adi-replica'`
   then append its public key to `/var/lib/adi-worker/.ssh/authorized_keys` with:
   `from="100.112.158.79,140.238.91.73",command="/usr/bin/rrsync /var/lib/ai-discovery/snapshots",no-pty,no-agent-forwarding,no-X11-forwarding`
   (`rrsync` is chrooted at that dir; the target path in `adi-run.sh` is `.`).
4. Enable: `ssh oracle 'sudo systemctl enable --now adi-db-tunnel && sudo systemctl enable --now adi-run.timer'`
5. Seed the root known_hosts so the tunnel's BatchMode ssh trusts Hetzner:
   `ssh oracle 'sudo mkdir -p /root/.ssh && sudo ssh-keyscan -t ed25519,rsa 100.109.237.19 | sudo tee -a /root/.ssh/known_hosts'`
6. Hetzner side: create the non-root account, its `authorized_keys` (above), the
   tailnet-only sshd listener (socket + sshd_config drop-ins), and make
   `/var/lib/ai-discovery/snapshots` owned by `adi-worker`.

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

`adi:current` is built here and never pulled. If it is missing, `adi-run.sh`
now fails loudly in the first second, records `IMAGE_MISSING` and the reason in
`latest.json`, and the unit's `OnFailure=` starts `adi-alert@`. That check exists
because a pruned image plus a misplaced `OnFailure=` meant 51 daily runs failed
unnoticed; see
[`docs/INCIDENT_2026-09-28_ACQUISITION_OUTAGE.md`](../../docs/INCIDENT_2026-09-28_ACQUISITION_OUTAGE.md).

## Weekly field-guide writer

`adi-writer.timer` runs at 02:00 UTC Sundays. It accepts acquisition evidence
only after a successful run in the last 48 hours. It compares a read-only
Postgres snapshot against the last successful write per guide, or the last
content commit on first use. It also checks for changed source captures and
guide sources due for a 30-day recheck. Coming-soon candidates need current
official evidence from at least two URLs across three relevant topics, including
a documented crawler, commercial or measurement control. The writer tries
the surfaces least recently attempted first and caps each run at 12 Sonnet
invocations, counting write and review calls.

Deploy it with `bash deploy/writer/deploy.sh oracle`, then
`sudo systemctl enable --now adi-writer.timer`. That script installs the runner
into the root-owned `/opt/adi-writer`, pins
`@anthropic-ai/claude-code@2.1.327` and `yaml@2.8.1` in `/opt/adi-writer/tools`,
clones the repository into `/opt/adi-writer/checkout`, installs both units, and
refuses to finish unless `/etc/claude-writer/env` (root, 0600),
`/etc/ai-discovery/env`, `/opt/adi-writer/guard/merge-guard.sh`, the pinned CLI
and a running `adi-db-tunnel.service` are all present. The ledger reader uses
the local `postgres:17-alpine` image over that tunnel. Progress is written to
`/var/lib/adi-writer`; GitHub actions use the existing Oracle `ubuntu` CLI
login. The isolated, unprivileged Claude process receives its subscription
credential only from the root-only `/etc/claude-writer/env` through systemd.
Its sole tool is WebFetch for the supplied source hosts. The coordinator applies
the proposed YAML only after checking the fetch transcript, schema, source URLs,
attribution and editorial budgets.

Run on demand with `sudo systemctl start adi-writer.service`. Pause with
`sudo systemctl disable --now adi-writer.timer`; `systemctl stop
adi-writer.service` also cuts a run in flight.

Every candidate goes through a PR. The existing web CI runs the build, Vitest
and Playwright. For a normal-sized update the writer runs an independent review
pass over the exact head diff and records the verdict through the repository
guard's own `record` command; it merges only when that guard then answers 0 for
the same head, with the head pinned on the merge. Changes over 80
added/deleted YAML lines and all promotions are held for an owner decision.
Promotions remove their Coming-soon entry mechanically in the same PR. The
existing production deployment follows merges to `main`.

Run summaries go to [Weekly content updates](https://github.com/Rajeev-SG/ai-discovery-intelligence/issues/76).
The writer exits nonzero on failures so `adi-alert@` records them. To prove
the content gate on Oracle without changing a page or using Claude, run
`sudo /usr/local/bin/node /opt/adi-writer/runner/adi-writer.mjs --prove-gate`.
