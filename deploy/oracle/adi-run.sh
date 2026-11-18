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
set -euo pipefail

STATE_DIR=/var/lib/ai-discovery
STATUS_DIR=$STATE_DIR/status
LOG_DIR=$STATE_DIR/runs
ENV_FILE=/etc/ai-discovery/env
IMAGE=adi:current
APP_DIR=/opt/ai-discovery/app
API_HEALTH_URL=${ADI_API_HEALTH_URL:-http://iyercyduhzplx2m7ldqqz0cp.89.167.5.185.sslip.io/health}
# The non-root adi-worker account on Hetzner, over the tailnet on port 2222. The
# default :22 is served by Tailscale SSH (interactive browser auth), unusable by
# an unattended timer; :2222 is a tailnet-bound real-sshd listener with per-key
# permitopen/rrsync restrictions that refuses root.
REPLICA_TARGET=${ADI_SNAPSHOT_REPLICA_TARGET:-adi-worker@100.109.237.19}
REPLICA_PORT=${ADI_SNAPSHOT_REPLICA_PORT:-2222}
# rrsync is chrooted at /var/lib/ai-discovery/snapshots, so the target is ".".
REPLICA_PATH=${ADI_SNAPSHOT_REPLICA_PATH:-.}
REPLICA_KEY=${ADI_SNAPSHOT_REPLICA_KEY:-/etc/ai-discovery/replica-key}

mkdir -p "$STATUS_DIR" "$LOG_DIR" "$STATE_DIR/snapshots" "$STATE_DIR/dagster-home"
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
log="$LOG_DIR/run-${started//:/}.log"

# Under `set -e`, any unexpected non-zero exit must still leave a status file
# behind. Without this, a single failing command could abort the script before
# latest.json is rewritten, which is the same silent-staleness mode this unit
# was fixed for.
wrote_status=0
aborted() {
  rc=$?
  [ "$wrote_status" -eq 0 ] || return 0
  tmp="$STATUS_DIR/.latest.json.tmp"
  printf '{"started_at": "%s", "finished_at": "%s", "ok": 0, "run_exit": %s, "replicated": 0, "api_evidence_items": -1, "error": "aborted_before_status", "log": "%s"}\n' \
    "$started" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$rc" "$log" >"$tmp"
  mv "$tmp" "$STATUS_DIR/latest.json"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) RUN_ABORTED rc=$rc action=inspect_log" \
    >>"$STATUS_DIR/failures.log"
}
trap aborted EXIT

run_rc=0
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Docker image $IMAGE is missing locally; rebuilding from $APP_DIR." >>"$log"
  docker build -f "$APP_DIR/deploy/oracle/Dockerfile.acquisition" -t "$IMAGE" "$APP_DIR" \
    >>"$log" 2>&1 || run_rc=$?
fi

if [ "$run_rc" -eq 0 ]; then
  docker run --pull=never --rm --name adi-run \
    --network host \
    --env-file "$ENV_FILE" \
    --memory 6g --cpus 2 \
    -v "$STATE_DIR":/data \
    "$IMAGE" \
      >>"$log" 2>&1 || run_rc=$?
fi

# Durable-state replication: the private snapshot store is the only state the
# worker owns; the ledger/claims live in the Hetzner Postgres. A failed
# replication never fails the run, but it is recorded so the gap is visible.
replicated=0
if [ "$run_rc" -eq 0 ]; then
  if rsync -a --delete -e "ssh -p $REPLICA_PORT -i $REPLICA_KEY -o BatchMode=yes -o ConnectTimeout=15" \
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
wrote_status=1

if [ "$ok" -ne 1 ]; then
  echo "Acquisition failed (Docker exit $run_rc, API evidence items $api_items). See $log." >&2
  exit 1
fi
