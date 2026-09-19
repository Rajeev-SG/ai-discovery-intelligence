#!/usr/bin/env bash
# Container entrypoint for the evidence API (issue #9).
#
# Creates the ledger tables idempotently (SQLAlchemy create_all, the repo's own
# init path) and then serves the API. create_all is safe to re-run and leaves
# existing tables and rows untouched, so a restart never corrupts canonical
# evidence.
set -euo pipefail

python - <<'PY'
import sys
sys.path.insert(0, "/app/src")
from ai_discovery.claims import create_ledger_engine, init_ledger
from ai_discovery.db import get_engine
from ai_discovery.models import Base

engine = get_engine()  # the shared engine (evidence tables from issue #2)
Base.metadata.create_all(engine)
init_ledger(engine)    # ledger tables (claim/study/metric/locator/evidence/event/brief)
print("ledger schema ensured", file=sys.stderr)
PY

exec uvicorn ai_discovery.api:app --host 0.0.0.0 --port 8000
