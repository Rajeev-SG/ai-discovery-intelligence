#!/usr/bin/env bash
# Deploy the ai-discovery-intelligence acquisition worker to the Oracle VPS
# (issue #9). Mirrors the proven ad-platform-intelligence pattern:
# rsync tree -> docker build adi:current -> install systemd units.
#
# One-time manual steps (documented in README.md, not automated here because
# they change credentials/authorised keys on the Hetzner host):
#   1. create /etc/ai-discovery/env on Oracle (mode 600)
#   2. install the two restricted keys into Hetzner authorized_keys
#   3. systemctl enable --now adi-db-tunnel && systemctl enable --now adi-run.timer
set -euo pipefail

HOST=${1:-oracle}
APP_DIR=/opt/ai-discovery/app

SRC=$(cd "$(dirname "$0")/../.." && pwd)   # repo root (deploy/oracle/../..)
test -f "$SRC/pyproject.toml" || { echo "refusing to deploy: $SRC is not the repo root" >&2; exit 1; }

# Sync the repository root the script lives in, not the caller's working
# directory, so `bash ~/path/deploy.sh` from anywhere builds the same tree.
# proof/ is kept because the acquisition image re-verifies quotes against
# proof/claim_ledger/captures at run time.
rsync -a --delete \
  --exclude .git --exclude .venv --exclude web \
  --exclude node_modules --exclude .pytest_cache \
  --exclude "/proof/*" --include "/proof/claim_ledger/" \
  --include "/proof/claim_ledger/captures/" --include "/proof/claim_ledger/captures/***" \
  --exclude "/proof/**" \
  "$SRC/" "$HOST:$APP_DIR/"

ssh "$HOST" "cd $APP_DIR && docker build -f deploy/oracle/Dockerfile.acquisition -t adi:current ."

scp -q deploy/oracle/adi-run.sh "$HOST:/tmp/adi-run.sh"
scp -q deploy/oracle/adi-run.service deploy/oracle/adi-run.timer \
        deploy/oracle/adi-alert@.service deploy/oracle/adi-db-tunnel.service \
      "$HOST:/tmp/"
ssh "$HOST" "sudo install -m 0755 /tmp/adi-run.sh /usr/local/sbin/adi-run && \
  sudo install -m 0644 /tmp/adi-run.service /tmp/adi-run.timer /tmp/adi-alert@.service /tmp/adi-db-tunnel.service /etc/systemd/system/ && \
  sudo systemctl daemon-reload"

echo "deployed. On the host, enable with:"
echo "  systemctl enable --now adi-db-tunnel && systemctl enable --now adi-run.timer"
