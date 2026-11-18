#!/usr/bin/env bash
# Deploy the weekly field-guide writer to the Oracle VPS (issue #75).
#
# Layout on the host:
#   /opt/adi-writer/runner    this directory's files (root-owned, 0755)
#   /opt/adi-writer/tools     pinned Claude Code CLI + yaml (npm)
#   /opt/adi-writer/checkout  a real clone of this repository (root-owned)
#   /opt/adi-writer/guard     the owner's merge guard, installed outside this repo
#   /var/lib/adi-writer       write progress and pending PR state (systemd StateDirectory)
#
# The subscription credential is never handled here. It lives in
# /etc/claude-writer/env (root, 0600) and reaches the Claude child only through
# systemd's EnvironmentFile=.
set -euo pipefail

HOST=${1:-oracle}
ROOT=/opt/adi-writer
REPO=https://github.com/Rajeev-SG/ai-discovery-intelligence.git
SRC=$(cd "$(dirname "$0")" && pwd)

ssh "$HOST" "sudo install -d -m 0755 $ROOT $ROOT/runner $ROOT/tools $ROOT/guard"

rsync -a --delete "$SRC/" "$HOST:/tmp/adi-writer-runner/"
ssh "$HOST" "sudo rsync -a --delete /tmp/adi-writer-runner/ $ROOT/runner/ && \
  sudo chown -R root:root $ROOT/runner && sudo rm -rf /tmp/adi-writer-runner"

# Pinned toolchain. The writer never upgrades itself mid-run.
ssh "$HOST" "cd $ROOT/tools && sudo npm install --silent --no-audit --no-fund \
  --save-exact @anthropic-ai/claude-code@2.1.327 yaml@2.8.1 && \
  sudo chown -R root:root $ROOT/tools"

# The writer edits and pushes from its own checkout, never the live deploy tree.
ssh "$HOST" "set -e
  if [ ! -d $ROOT/checkout/.git ]; then
    sudo git clone --quiet $REPO $ROOT/checkout
  fi
  sudo git -C $ROOT/checkout fetch --quiet origin main
  sudo git -C $ROOT/checkout checkout --quiet --detach origin/main
  sudo chown -R root:root $ROOT/checkout"

scp -q "$SRC/adi-writer.service" "$SRC/adi-writer.timer" "$HOST:/tmp/"
ssh "$HOST" "sudo install -m 0644 /tmp/adi-writer.service /tmp/adi-writer.timer /etc/systemd/system/ && \
  sudo rm -f /tmp/adi-writer.service /tmp/adi-writer.timer && sudo systemctl daemon-reload"

# Fail loudly at deploy time rather than at 02:00 on Sunday.
ssh "$HOST" 'set -e
  test -f /etc/claude-writer/env || { echo "MISSING /etc/claude-writer/env (root, 0600)" >&2; exit 1; }
  sudo test -f /etc/claude-writer/env
  test -f /etc/ai-discovery/env || { echo "MISSING /etc/ai-discovery/env" >&2; exit 1; }
  test -x /opt/adi-writer/guard/merge-guard.sh || { echo "MISSING /opt/adi-writer/guard/merge-guard.sh" >&2; exit 1; }
  test -x /opt/adi-writer/tools/node_modules/.bin/claude || { echo "MISSING claude CLI" >&2; exit 1; }
  sudo -n systemctl is-active adi-db-tunnel.service >/dev/null || { echo "adi-db-tunnel is not running" >&2; exit 1; }
  echo "writer prerequisites OK"'

echo "deployed. Enable the weekly run with:"
echo "  ssh $HOST 'sudo systemctl enable --now adi-writer.timer'"
echo "Run one now (manual proof) with:"
echo "  ssh $HOST 'sudo systemctl start adi-writer.service'"
