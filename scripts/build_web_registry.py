"""Vendor config/surfaces.yaml into web/lib/generated-registry.json.

The observation plane builds with `web/` as its root, where `../config` is not
part of the deployment. Committing a generated copy keeps the web app
self-contained and deployable from `web/` alone; `config/surfaces.yaml` remains
the source of truth, and `web/lib/registry.ts` prefers the live file when it is
present (local dev, monorepo builds).

Run: uv run python scripts/build_web_registry.py (CI checks it is current).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "config" / "surfaces.yaml"
OUT = REPO / "web" / "lib" / "generated-registry.json"


def main() -> int:
    raw = yaml.safe_load(SOURCE.read_text())
    payload = {
        "version": raw.get("version", 1),
        "last_reviewed": str(raw.get("last_reviewed", "unknown")),
        "surfaces": raw.get("surfaces", []),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['surfaces'])} surfaces -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
