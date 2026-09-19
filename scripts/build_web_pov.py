"""Vendor pov/state.yaml into web/lib/generated-pov.json (issue #49).

The web app builds with `web/` as its project root (Vercel), where `../pov` is
not part of the deployment. Committing a generated copy keeps the POV surface
self-contained and deployable from `web/` alone, exactly as
`scripts/build_web_registry.py` does for the surface registry. `pov/state.yaml`
remains canonical, and the deterministic POV gate is not re-implemented here:
the projection reuses the tested domain model (`ai_discovery.pov`) so the
confidence and contested state rendered in the UI are the same values the
generator and changelog use.

Run: python scripts/build_web_pov.py (CI checks the artifact is current).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

SYSTEM_PROPS = {
    "pov-retrieval-systems": "retrieval",
    "pov-channel-prioritisation": "channel",
    "pov-commerce-ads": "commerce",
    "pov-measurement": "measurement",
}


def _iso(value):
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def build_payload(state) -> dict:
    propositions = []
    for prop in state.propositions:
        propositions.append(
            {
                "id": prop.id,
                "section": prop.section,
                "base_text": prop.base_text,
                "topics": list(prop.topics),
                "confidence": prop.confidence().value,
                "contested": prop.is_contested,
                "last_reviewed": _iso(prop.last_reviewed),
                "supporting": [_bullet(b) for b in prop.supporting],
                "contradicting": [_bullet(b) for b in prop.contradicting],
            }
        )

    changelog = []
    for rev in state.changelog:
        changelog.append(
            {
                "proposition_id": rev.proposition_id,
                "changed_at": _iso(rev.changed_at),
                "reason": rev.reason,
                "event_id": rev.event_id,
                "evidence_ids": list(rev.evidence_ids),
                "old_statement": rev.old_statement,
                "new_statement": rev.new_statement,
                "significance": rev.significance,
                "confidence": rev.confidence,
            }
        )

    return {
        "source": "pov/state.yaml",
        "version": state.version,
        "propositions": propositions,
        "changelog": changelog,
    }


def _bullet(bullet) -> dict:
    return {
        "slot": bullet.slot,
        "polarity": bullet.polarity,
        "text": bullet.text,
        "claim_id": bullet.claim_id,
        "event_id": bullet.event_id,
        "confidence": bullet.confidence.value,
        "value_number": bullet.value_number,
        "value_text": bullet.value_text,
        "effective_at": _iso(bullet.effective_at),
        "added_at": _iso(bullet.added_at),
    }


def main() -> int:
    # Import after sys.path is set so the domain model is the canonical one.
    from ai_discovery.pov import load_state

    state = load_state(REPO / "pov" / "state.yaml")
    payload = build_payload(state)
    out = REPO / "web" / "lib" / "generated-pov.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {len(payload['propositions'])} propositions, "
        f"{len(payload['changelog'])} changelog entries -> {out.relative_to(REPO)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
