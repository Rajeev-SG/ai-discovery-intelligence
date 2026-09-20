"""Read-only evidence-feed API (FastAPI).

Serves normalised evidence for the observation plane (issue #1 frontend). Raw
snapshots are private and are never exposed: only metadata, an excerpt and links.
"""

from __future__ import annotations

import datetime as dt
import json

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .db import get_sessionmaker
from .models import DiscoveredCandidate, EvidenceItem, Source, SourceCheck
from .settings import get_settings

app = FastAPI(
    title="AI Discovery Intelligence — Evidence Feed",
    version="1.0.0",
    description="Read-only normalised evidence and source health for the observation plane.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_db() -> Session:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    evidence = db.scalar(select(func.count()).select_from(EvidenceItem)) or 0
    sources = db.scalar(select(func.count()).select_from(Source)) or 0
    degraded = (
        db.scalar(select(func.count()).select_from(Source).where(Source.health_status != "ok")) or 0
    )
    candidates = db.scalar(select(func.count()).select_from(DiscoveredCandidate)) or 0
    return {
        "status": "degraded" if degraded else "ok",
        "evidence_items": evidence,
        "sources": sources,
        "sources_not_ok": degraded,
        "discovered_candidates": candidates,
    }


@app.get("/evidence", tags=["evidence"])
def list_evidence(
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
    source_class: str | None = None,
    publisher: str | None = None,
    topic: str | None = None,
    q: str | None = None,
    include_candidates: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Evidence feed, newest publication/observation first."""
    stmt = select(EvidenceItem)
    if not include_candidates:
        stmt = stmt.where(EvidenceItem.is_candidate.is_(False))
    if source_class:
        stmt = stmt.where(EvidenceItem.source_class == source_class)
    if publisher:
        stmt = stmt.where(EvidenceItem.publisher == publisher)
    if q:
        stmt = stmt.where(EvidenceItem.title.ilike(f"%{q}%"))
    if topic:
        # Portable across PostgreSQL (JSON) and the SQLite test database: match the
        # topic as a JSON string element rather than relying on a dialect operator.
        if db.bind.dialect.name == "sqlite":
            stmt = stmt.where(func.json_extract(EvidenceItem.topics, "$").like(f'%"{topic}"%'))
        else:
            topic_json = json.dumps([topic])
            stmt = stmt.where(
                text("evidence_item.topics::jsonb @> :topic_json").bindparams(topic_json=topic_json)
            )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(func.coalesce(EvidenceItem.published_at, EvidenceItem.observed_at).desc())
        .offset(offset)
        .limit(limit)
    ).all()
    items = [serialise_evidence(row) for row in rows]
    return {"total": total, "count": len(items), "limit": limit, "offset": offset, "items": items}


@app.get("/evidence/{evidence_id}", tags=["evidence"])
def get_evidence(evidence_id: str, db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    row = db.get(EvidenceItem, evidence_id)
    if row is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return serialise_evidence(row, full_excerpt=True)


@app.get("/sources", tags=["sources"])
def list_sources(db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    rows = db.scalars(select(Source).order_by(Source.source_class, Source.id)).all()
    return {"count": len(rows), "items": [serialise_source(row) for row in rows]}


@app.get("/sources/{source_id}/checks", tags=["sources"])
def source_checks(
    source_id: str,
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    if db.get(Source, source_id) is None:
        raise HTTPException(status_code=404, detail="source not found")
    rows = db.scalars(
        select(SourceCheck)
        .where(SourceCheck.source_id == source_id)
        .order_by(SourceCheck.checked_at.desc())
        .limit(limit)
    ).all()
    return {
        "source_id": source_id,
        "items": [
            {
                "checked_at": _iso(r.checked_at),
                "status": r.status,
                "http_status": r.http_status,
                "latency_ms": r.latency_ms,
                "items_new": r.items_new,
                "content_changed": r.content_changed,
                "error": r.error,
            }
            for r in rows
        ],
    }


@app.get("/candidates", tags=["discovery"])
def list_candidates(
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
    include_registry: bool = False,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Discovery-lane candidates. Non-canonical until validated."""
    stmt = select(DiscoveredCandidate).order_by(DiscoveredCandidate.first_seen_at.desc())
    if not include_registry:
        # default: unvalidated, non-registry discovery candidates only
        stmt = stmt.where(
            DiscoveredCandidate.in_registry.is_(False),
            DiscoveredCandidate.validation_status == "unvalidated",
        )
    rows = db.scalars(stmt.limit(limit)).all()
    return {
        "count": len(rows),
        "note": "Candidates are non-canonical discovery signals until validated.",
        "items": [
            {
                "id": r.id,
                "url": r.url,
                "canonical_url": r.canonical_url,
                "host": r.host,
                "title": r.title,
                "discovered_via": r.discovered_via,
                "discovery_query": r.discovery_query,
                "source_class_guess": r.source_class_guess,
                "topics": r.topics,
                "in_registry": r.in_registry,
                "validation_status": r.validation_status,
                "first_seen_at": _iso(r.first_seen_at),
                "last_seen_at": _iso(r.last_seen_at),
            }
            for r in rows
        ],
    }


def serialise_evidence(row: EvidenceItem, *, full_excerpt: bool = False) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "publisher": row.publisher,
        "url": row.url,
        "canonical_url": row.canonical_url,
        "source_id": row.source_id,
        "source_class": row.source_class,
        "topics": row.topics or [],
        "language": row.language,
        "region": row.region,
        # published vs observed are separate fields: a "modified" timestamp is
        # never promoted to publication date (see issue #4 finding).
        "published_at": _iso(row.published_at),
        "published_at_source": row.published_at_source,
        "modified_at": _iso(row.modified_at),
        "observed_at": _iso(row.observed_at),
        "capture_hash": row.capture_hash,
        "raw_sha256": row.raw_sha256,
        "capture_hash_note": "sha256 of whitespace-normalised extracted text",
        "text_chars": row.text_chars,
        "excerpt": row.excerpt if full_excerpt else (row.excerpt or "")[:300],
        "fetch_mode": row.fetch_mode,
        "http_status": row.http_status,
        "content_type": row.content_type,
        "extractor": row.extractor,
        "is_candidate": row.is_candidate,
        "validation_status": row.validation_status,
        "snapshot_available": bool(row.snapshot_path),
    }


def serialise_source(row: Source) -> dict:
    return {
        "id": row.id,
        "publisher": row.publisher,
        "source_class": row.source_class,
        "url": row.url,
        "topics": row.topics or [],
        "preferred_fetch": row.preferred_fetch,
        "fetch_mode": row.fetch_mode,
        "health_status": row.health_status,
        "last_check_at": _iso(row.last_check_at),
        "last_success_at": _iso(row.last_success_at),
        "last_content_hash": row.last_content_hash,
        "last_http_status": row.last_http_status,
        "consecutive_failures": row.consecutive_failures,
        "last_error": row.last_error,
        "enabled": row.enabled,
    }


def _ledger_engine(db: Session):
    """The engine backing the request session, for the ledger read helpers."""

    return db.get_bind()


@app.get("/claims", tags=["claims"])
def list_claims(
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
    surface: str | None = None,
    topic: str | None = None,
    min_confidence: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Validated claims from the ledger, newest first.

    Raw captures stay private: each claim carries the evidence hash and
    availability plus source-derived confidence and freshness, never a snapshot
    path or capture text.
    """

    from .claims import load_expanded_claims
    from .observations import claim_view

    # Filter, order and paginate in SQL so a request touches only its page. A
    # confidence floor is applied in SQL too when asked for.
    rank = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    floor = rank.get(min_confidence or "", -1)
    floor_key = {v: k for k, v in rank.items()}.get(floor)
    rows = [
        claim_view(r)
        for r in load_expanded_claims(
            _ledger_engine(db),
            topic=topic,
            surface=surface,
            # Over-fetch only when a confidence floor must be applied post-hoc.
            limit=limit if floor_key is None else None,
            offset=offset if floor_key is None else 0,
        )
    ]
    if floor_key is not None:
        rows = [r for r in rows if rank.get(r.get("confidence"), 0) >= floor]
        rows = rows[offset : offset + limit]
    return {"total": len(rows), "count": len(rows), "limit": limit, "offset": offset, "items": rows}


@app.get("/events", tags=["events"])
def list_events(
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
    surface: str | None = None,
    event_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    """Typed change events, newest first, deduplicated by stable key."""

    from .observations import event_view, load_events

    events = load_events(db)
    if surface:
        events = [e for e in events if surface in e.surfaces]
    if event_type:
        events = [e for e in events if e.event_type.value == event_type]
    # Newest first by effective/published time, then observation time, before the
    # limit is applied, so the page always contains the newest events.
    def _sort_key(e):
        stamp = e.effective_from or e.published_at or e.observed_at
        return stamp.timestamp() if stamp else 0.0

    events = sorted(events, key=_sort_key, reverse=True)
    items = [event_view(e) for e in events[:limit]]
    return {"count": len(items), "limit": limit, "items": items}


@app.get("/brief", tags=["brief"])
def get_brief(db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    """The latest persisted weekly brief, or an explicit empty state."""

    from .observations import load_brief

    brief = load_brief(db)
    if brief is None:
        return {"state": "empty", "items": [], "note": "No weekly brief has been generated yet."}
    return {"state": "ready", **brief}


@app.get("/reconciliation", tags=["reconciliation"])
def list_reconciliation(db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    """Real reconciliation over the persisted ledger.

    Compares stored claims that share a surface and subject but disagree. Empty
    when no persisted claims conflict — the endpoint never returns a fixed,
    hardcoded case.
    """

    from .claims import load_expanded_claims
    from .reconciliation import reconcile_persisted

    results = reconcile_persisted(load_expanded_claims(_ledger_engine(db)))
    return {
        "count": len(results),
        "items": [
            {
                "claim_ids": list(r.claim_ids),
                "state": r.state,
                "relationship": r.relationship,
                "confidence_adjustment": r.confidence_adjustment,
                "differences": list(r.differences),
                "unknown_dimensions": list(r.unknown_dimensions),
                "interpretation": r.interpretation,
            }
            for r in results
        ],
    }


@app.get("/surface-evidence", tags=["surfaces"])
def list_surface_evidence(db: Session = Depends(get_db)) -> dict:  # noqa: B008 — FastAPI DI
    """Evidence projection for every surface with a claim or change event.

    One request instead of one per surface; surfaces with neither are absent so
    the caller renders its own explicit no-evidence state.
    """

    from .claims import load_expanded_claims
    from .observations import claim_view, load_events, surface_evidence

    claims = [claim_view(r) for r in load_expanded_claims(_ledger_engine(db))]
    events = load_events(db)
    by_surface = surface_evidence(claims, events)
    return {"count": len(by_surface), "surfaces": by_surface}


@app.get("/surfaces/{surface_id}/evidence", tags=["surfaces"])
def get_surface_evidence(
    surface_id: str,
    db: Session = Depends(get_db),  # noqa: B008 — FastAPI DI
) -> dict:
    """Claims + latest material change for one surface, or an explicit no-evidence state."""

    from .claims import load_expanded_claims
    from .observations import claim_view, load_events, surface_evidence

    claims = [claim_view(r) for r in load_expanded_claims(_ledger_engine(db))]
    events = load_events(db)
    entry = surface_evidence(claims, events).get(surface_id)
    if entry is None:
        return {
            "surface": surface_id,
            "evidence_state": "no_evidence",
            "evidence_note": "No validated claim is linked to this surface yet.",
            "claims": [],
            "latest_change": None,
        }
    return entry


# --------------------------------------------------------------------------- #
# Canonical mechanics projection (Phase 2, issue #56)
# --------------------------------------------------------------------------- #


def _surface_registry_ids() -> list[str]:
    """Registry surface ids, in canonical order. Never derived from claims."""

    from .registry import load_surfaces_config

    try:
        return load_surfaces_config().ids()
    except (FileNotFoundError, OSError, ValueError):
        return []


@app.get("/mechanics", tags=["mechanics"])
def list_mechanics(db: Session = Depends(get_db)) -> dict:  # noqa: B008 - FastAPI DI
    """Marketer-safe mechanics projection for every registry surface.

    Real, validated claims only: a dimension with no supporting claim is an
    explicit ``unknown``. No private snapshot data and no capture text is
    exposed - each evidenced dimension carries the claim id, source class,
    evidence class, publisher, public URL, dates, confidence and methodology.
    """

    from .claims import load_expanded_claims
    from .mechanics import (
        MECHANICS_DIMENSIONS,
        mechanics_view,
        project_all,
        unmapped_claim_surfaces,
    )

    # Raw expanded ledger rows: the projection needs each claim's methodology and
    # provenance, not just the product-shaped claim view.
    registry_ids = _surface_registry_ids()
    claims = load_expanded_claims(_ledger_engine(db))
    projection = project_all(registry_ids, claims)
    unmapped = unmapped_claim_surfaces(registry_ids, claims)
    return {
        "dimension_count": len(MECHANICS_DIMENSIONS),
        "count": len(projection),
        "surfaces": {sid: mechanics_view(m) for sid, m in projection.items()},
        # Diagnostic only: claim surface ids absent from the registry (drift).
        "unmapped_claim_surfaces": unmapped,
    }


@app.get("/surfaces/{surface_id}/mechanics", tags=["mechanics"])
def get_surface_mechanics(
    surface_id: str,
    db: Session = Depends(get_db),  # noqa: B008 - FastAPI DI
) -> dict:
    """The canonical mechanics projection for one surface.

    An unknown surface (not in the registry) returns an explicit empty state
    rather than a fabricated projection.
    """

    from .claims import load_expanded_claims
    from .mechanics import mechanics_view, project_surface

    if surface_id not in _surface_registry_ids():
        return {
            "surface": surface_id,
            "state": "unknown_surface",
            "note": "Surface is not in the canonical registry.",
            "dimensions": [],
        }
    claims = load_expanded_claims(_ledger_engine(db))
    return mechanics_view(project_surface(surface_id, claims))
