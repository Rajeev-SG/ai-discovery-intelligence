"""Wire the weekly executive brief into the production pipeline (issue #48).

`docs/PIPELINES.md` lists `weekly_exec_brief` as step 14, and `brief.py`
implements the generator, but nothing in the acquisition/extraction lane ever
built one — so `/brief` was permanently empty on the live product even once real
material changes existed.

This module closes that gap deterministically and without a model:

* candidates come from the **persisted change events** (each already grounded in
  a validated, quote-verified claim);
* the framing text (change / why_it_matters / agency_action) is chosen from the
  event type via `config/brief_copy.yaml`, so the same event always produces the
  same words and facts come from the claim, never from an LLM;
* the existing `BriefGenerator` applies the window, confidence floor, soft
  target and hard cap exactly as configured in `config/executive_policy.yaml`.

The brief is persisted through `persist_brief` and read back by `GET /brief`.
It is idempotent per generation window: re-running with the same events over the
same week yields the same items.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .brief import BriefGenerator, BriefItem, ConfidenceLabel
from .pov import significance_of

_COPY_PATH = Path(__file__).resolve().parents[2] / "config" / "brief_copy.yaml"

# Confidence labels in the brief's own vocabulary.
_LABEL = {
    "high": ConfidenceLabel.HIGH,
    "medium_high": ConfidenceLabel.MEDIUM_HIGH,
    "medium": ConfidenceLabel.MEDIUM,
    "low": ConfidenceLabel.LOW,
    "unresolved": ConfidenceLabel.UNRESOLVED,
}


def _load_copy() -> dict[str, Any]:
    return yaml.safe_load(_COPY_PATH.read_text())


def _framing(event_type: str) -> tuple[str, str]:
    copy = _load_copy()
    entry = copy.get("by_event_type", {}).get(event_type) or copy["default"]
    return entry["why_it_matters"], entry["agency_action"]


def _confidence_label(claim: dict[str, Any] | None) -> ConfidenceLabel:
    label = (claim or {}).get("confidence") or "medium"
    return _LABEL.get(label, ConfidenceLabel.MEDIUM)


def brief_item_from_event(event: dict[str, Any], claim: dict[str, Any] | None) -> BriefItem:
    """One deterministic brief item from a persisted event + its grounding claim."""

    why, action = _framing(event.get("event_type", ""))
    return BriefItem(
        change=event.get("title") or (claim or {}).get("statement") or "",
        why_it_matters=why,
        agency_action=action,
        confidence=_confidence_label(claim),
        significance=significance_of(claim or {}),
        evidence_ids=list(event.get("claims") or []),
        surfaces=list(event.get("surfaces") or []),
        is_watch_item=False,
        effective_from=_parse(event.get("effective_from")),
        published_at=_parse(event.get("published_at")),
        observed_at=_parse(event.get("observed_at")),
    )


def _parse(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def generate_brief_items(
    events: list[dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
    *,
    reference: dt.datetime | None = None,
    generator: BriefGenerator | None = None,
) -> list[BriefItem]:
    """Build and gate the weekly brief from persisted events (no model)."""

    candidates = [
        brief_item_from_event(event, _claim_for(event, claims_by_id)) for event in events
    ]
    candidates = [c for c in candidates if c.change and c.evidence_ids]
    gen = generator or BriefGenerator()
    if reference is None:
        return gen.generate(candidates)
    return gen.generate(candidates, window_start=_week_start(reference), window_end=reference)


def _week_start(reference: dt.datetime) -> dt.datetime:
    ref = reference if reference.tzinfo else reference.replace(tzinfo=dt.UTC)
    return ref - dt.timedelta(days=7)


def _claim_for(event: dict[str, Any], claims_by_id: dict[str, dict[str, Any]]) -> dict | None:
    for claim_id in event.get("claims") or []:
        if claim_id in claims_by_id:
            return claims_by_id[claim_id]
    return None


def build_and_persist_brief(db, *, reference: dt.datetime | None = None) -> dict[str, Any] | None:
    """Read events + claims, build the brief, persist it, and return the payload.

    Returns ``None`` when nothing qualifies (a valid weekly outcome) — the caller
    does not fabricate a brief. Only persist when there is at least one item, so
    `/brief` keeps its explicit empty state rather than an empty "ready" body.
    """

    from .claims import load_expanded_claims
    from .observations import claim_view, load_events, persist_brief

    engine = db.get_bind()
    claims = [claim_view(row) for row in load_expanded_claims(engine)]
    claims_by_id = {c["claim_id"]: c for c in claims}
    events = [e.model_dump(mode="json") for e in load_events(db)]
    # event_view shape (already JSON-ready) so title/dates match the API.
    from .observations import event_view

    event_views = [event_view(e) for e in load_events(db)]
    items = generate_brief_items(event_views, claims_by_id, reference=reference)
    if not items:
        return None
    now = reference or dt.datetime.now(dt.UTC)
    payload = {
        "state": "ready",
        "generated_at": now.isoformat(),
        "window_start": (now - dt.timedelta(days=7)).isoformat(),
        "window_end": now.isoformat(),
        "items": [item.model_dump(mode="json") for item in items],
        "candidate_events": len(events),
    }
    persist_brief(db, payload)
    return payload
