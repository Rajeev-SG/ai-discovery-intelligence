#!/usr/bin/env bash
# One acquisition cycle on the Oracle VPS (issue #9): capture configured
# sources into private snapshots, extract quote-verified claims with
# Instructor/OpenRouter, then replicate the snapshot store to the durable
# Hetzner host so no unique durable state exists only on Oracle.
#
# Health signal: every run writes /var/lib/ai-discovery/status/latest.json
# (atomic rename) including the evidence API's live /health counts, so a
# scheduled run that fails — or a timer that never fires — is visible from
# latest.json plus `systemctl list-timers`. OnFailure=adi-alert@%n appends
# to /var/lib/ai-discovery/status/failures.log.
set -uo pipefail

STATE_DIR=/var/lib/ai-discovery
STATUS_DIR=$STATE_DIR/status
LOG_DIR=$STATE_DIR/runs
ENV_FILE=/etc/ai-discovery/env
IMAGE=adi:current
API_HEALTH_URL=${ADI_API_HEALTH_URL:-http://iyercyduhzplx2m7ldqqz0cp.89.167.5.185.sslip.io/health}
# Hetzner public IP, not the tailnet IP: the Hetzner host runs Tailscale SSH,
# which intercepts :22 on the tailnet address and demands interactive browser
# auth, so a key-restricted, unattended systemd tunnel can never authenticate
# over the tailnet. The public IP uses plain sshd with the restricted keys.
REPLICA_TARGET=${ADI_SNAPSHOT_REPLICA_TARGET:-root@89.167.5.185}
# rrsync roots at /var/lib/ai-discovery, so the target path is relative.
REPLICA_PATH=${ADI_SNAPSHOT_REPLICA_PATH:-snapshots/}
REPLICA_KEY=${ADI_SNAPSHOT_REPLICA_KEY:-/etc/ai-discovery/replica-key}

mkdir -p "$STATUS_DIR" "$LOG_DIR" "$STATE_DIR/snapshots" "$STATE_DIR/dagster-home"
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
log="$LOG_DIR/run-${started//:/}.log"

run_rc=0
docker run --rm --name adi-run \
  --network host \
  --env-file "$ENV_FILE" \
  --memory 6g --cpus 2 \
  -v "$STATE_DIR":/data \
  "$IMAGE" \
    >>"$log" 2>&1 || run_rc=$?

# Durable-state replication: the private snapshot store is the only state the
# worker owns; the ledger/claims live in the Hetzner Postgres. A failed
# replication never fails the run, but it is recorded so the gap is visible.
replicated=0
if [ "$run_rc" -eq 0 ]; then
  if rsync -a --delete -e "ssh -i $REPLICA_KEY -o BatchMode=yes -o ConnectTimeout=15" \
      "$STATE_DIR/snapshots/" "$REPLICA_TARGET:$REPLICA_PATH" \
      >>"$log" 2>&1; then
    replicated=1
  else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SNAPSHOT_REPLICATION_FAILED target=$REPLICA_TARGET" >>"$STATUS_DIR/failures.log"
  fi
fi

api_items=-1
api_json=$(curl -fsS -m 15 "$API_HEALTH_URL" 2>/dev/null || true)
if [ -n "$api_json" ]; then
  api_items=$(printf '%s' "$api_json" | grep -Eo '"evidence_items":[0-9]+' | grep -Eo '[0-9]+' || echo -1)
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ok=1
[ "$run_rc" -eq 0 ] || ok=0
[ "$api_items" -ge 0 ] 2>/dev/null || ok=0

status="$STATUS_DIR/.latest.json.tmp"
printf '{"started_at": "%s", "finished_at": "%s", "ok": %s, "run_exit": %s, "replicated": %s, "api_evidence_items": %s, "log": "%s"}\n' \
  "$started" "$finished" "$ok" "$run_rc" "$replicated" "$api_items" "$log" \
  >"$status"
mv "$status" "$STATUS_DIR/latest.json"

[ "$ok" -eq 1 ] || exit 1
