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
