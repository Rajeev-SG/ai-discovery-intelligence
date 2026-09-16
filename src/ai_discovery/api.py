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
