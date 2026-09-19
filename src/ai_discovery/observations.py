"""Read model for the observation plane (issue #23).

Wires the persisted domain layer — validated claims, change events and the
weekly brief — into product-shaped read views. Everything here is read-only and
keeps raw captures private: a view exposes claim values, the evidence link
(hash + availability), evidence-derived confidence, freshness and the latest
material change, never a filesystem path or capture text.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .change_events import ChangeEvent


def _iso(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.isoformat()


def _freshness(observed: dt.datetime | None) -> dict[str, Any]:
    """Freshness of a claim/capture, as an explicit state (never a guess)."""

    if observed is None:
        return {"state": "unknown", "age_days": None, "observed_at": None}
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=dt.UTC)
    age = (dt.datetime.now(dt.UTC) - observed).days
    if age <= 7:
        state = "fresh"
    elif age <= 45:
        state = "recent"
    elif age <= 180:
        state = "aging"
    else:
        state = "stale"
    return {"state": state, "age_days": age, "observed_at": _iso(observed)}


def claim_view(row: dict[str, Any]) -> dict[str, Any]:
    """Product shape for one claim from ``load_expanded_claims``."""

    metrics = row.get("metrics") or []
    evidence = row.get("evidence") or []
    detail = row.get("confidence_detail") or {}
    # The latest evidence row carries the observed_at used for freshness.
    latest_observed = None
    for entry in evidence:
        stamp = entry.get("fetched_at")
        if stamp and (latest_observed is None or stamp > latest_observed):
            latest_observed = stamp
    observed = _parse(latest_observed) or _parse((row.get("dates") or {}).get("observed_at"))
    return {
        "claim_id": row["claim_id"],
        "topic": row["topic"],
        "statement": row["statement"],
        "surfaces": row.get("surfaces") or [],
        "status": row.get("status"),
        "relationship": row.get("relationship"),
        "confidence": row.get("confidence"),
        "confidence_detail": {
            "score": detail.get("score"),
            "inputs": detail.get("inputs") or {},
            "rationale": detail.get("rationale") or [],
            "derived": True,
        },
        "value": [
            {
                "metric_id": m.get("metric_id"),
                "label": m.get("label"),
                "value_number": m.get("value_number"),
                "value_text": m.get("value_text"),
                "unit": m.get("unit"),
                "window": m.get("window"),
                "scope": m.get("scope"),
                "known": m.get("value_number") is not None or bool(m.get("value_text")),
            }
            for m in metrics
        ],
        "source": {
            "source_id": (row.get("source") or {}).get("source_id"),
            "publisher": (row.get("source") or {}).get("publisher"),
            "url": (row.get("source") or {}).get("url"),
            "source_class": (row.get("source") or {}).get("source_class"),
        },
        "provenance": [
            {
                "field_path": p.get("field_path"),
                "locator_kind": p.get("locator_kind"),
                "quote": p.get("quote"),
                "selector": p.get("selector"),
            }
            for p in (row.get("provenance") or [])
        ],
        # Private captures: hash + availability only.
        "evidence": [
            {
                "capture_hash": e.get("capture_hash"),
                "raw_sha256": e.get("raw_sha256"),
                "snapshot_available": bool(e.get("snapshot_available")),
                "http_status": e.get("http_status"),
                "fetched_at": e.get("fetched_at"),
            }
            for e in evidence
        ],
        "dates": row.get("dates") or {},
        "freshness": _freshness(observed),
    }


def _parse(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    try:
        return dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None


def surface_evidence(claims: list[dict[str, Any]], change_events: list[ChangeEvent]) -> dict[str, dict]:
    """Per-surface view: claims + latest material change, or an explicit no-evidence state."""

    by_surface: dict[str, dict] = {}
    for claim in claims:
        for surface in claim.get("surfaces") or []:
            entry = by_surface.setdefault(
                surface, {"surface": surface, "claims": [], "latest_change": None}
            )
            entry["claims"].append(claim)
    for event in sorted(change_events, key=lambda e: e.published_at or e.observed_at, reverse=True):
        for surface in event.surfaces:
            entry = by_surface.setdefault(
                surface, {"surface": surface, "claims": [], "latest_change": None}
            )
            if entry["latest_change"] is None:
                entry["latest_change"] = event_view(event)
    for surface, entry in by_surface.items():
        if not entry["claims"]:
            entry["evidence_state"] = "no_evidence"
            entry["evidence_note"] = "No validated claim is linked to this surface yet."
        else:
            entry["evidence_state"] = "evidenced"
            entry["evidence_note"] = None
    return by_surface


def event_view(event: ChangeEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type.value,
        "title": event.title,
        "description": event.description,
        "surfaces": list(event.surfaces),
        "claims": list(event.claims),
        "evidence_urls": list(event.evidence_urls),
        "observed_at": _iso(event.observed_at),
        "published_at": _iso(event.published_at),
        "effective_from": _iso(event.effective_from),
        "supersedes": event.supersedes,
        "source_hash": event.source_hash,
    }


def load_events(db: Session) -> list[ChangeEvent]:
    """Read persisted change events, newest first.

    Uses the ``change_event`` table when present (production); returns an empty
    list rather than inventing events when the store is empty.
    """

    from .claims import ChangeEventRow  # local import: optional table

    try:
        rows = db.scalars(
            select(ChangeEventRow).order_by(ChangeEventRow.observed_at.desc())
        ).all()
    except OperationalError:  # pragma: no cover - table absent in a ledger-only database
        return []
    return [ChangeEvent(**json.loads(r.payload)) for r in rows]


def load_brief(db: Session) -> dict[str, Any] | None:
    """The latest persisted weekly brief, or ``None`` when none exists."""

    from .claims import BriefSnapshotRow

    try:
        row = db.scalars(
            select(BriefSnapshotRow).order_by(BriefSnapshotRow.generated_at.desc()).limit(1)
        ).first()
    except OperationalError:  # pragma: no cover - table absent in a ledger-only database
        return None
    if row is None:
        return None
    payload = json.loads(row.payload)
    payload.setdefault("generated_at", _iso(row.generated_at))
    return payload


def persist_brief(db: Session, payload: dict[str, Any]) -> None:
    """Persist one generated brief so the product reads real output."""

    from .claims import BriefSnapshotRow

    db.add(BriefSnapshotRow(payload=json.dumps(payload)))
    db.commit()


def persist_events(db: Session, events: list[ChangeEvent]) -> int:
    """Append change events (idempotent by id) and return how many were added."""

    from .claims import ChangeEventRow

    added = 0
    for event in events:
        if db.get(ChangeEventRow, event.id) is not None:
            continue
        db.add(
            ChangeEventRow(
                id=event.id,
                event_type=event.event_type.value,
                title=event.title,
                surfaces=list(event.surfaces),
                dedupe_key=event.dedupe_key,
                payload=json.dumps(event.model_dump(mode="json")),
                observed_at=event.observed_at,
                published_at=event.published_at,
                effective_from=event.effective_from,
            )
        )
        added += 1
    db.commit()
    return added
