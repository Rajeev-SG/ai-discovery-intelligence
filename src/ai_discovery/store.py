"""Persist spider output into the canonical database (domain mapping only)."""

from __future__ import annotations

import datetime as dt

from dateutil import parser as date_parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters.gdelt import DiscoveryHit
from .discovery import record_candidates
from .hashing import evidence_id
from .models import EvidenceItem, Source, SourceCheck, utcnow


def _dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (ValueError, OverflowError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def store_articles(session: Session, items: list[dict]) -> int:
    """Insert new evidence rows; identical (url, capture_hash) is a no-op."""
    created = 0
    for item in items:
        existing = session.scalar(
            select(EvidenceItem).where(
                EvidenceItem.canonical_url == item["canonical_url"],
                EvidenceItem.capture_hash == item["capture_hash"],
            )
        )
        if existing is not None:
            continue
        session.add(
            EvidenceItem(
                id=evidence_id(item["canonical_url"], item["capture_hash"]),
                source_id=item.get("source_id"),
                candidate_id=item.get("candidate_id"),
                url=item["url"],
                canonical_url=item["canonical_url"],
                title=item.get("title") or item["canonical_url"],
                publisher=item.get("publisher"),
                source_class=item["source_class"],
                published_at=_dt(item.get("published_at")),
                published_at_source=item.get("published_at_source"),
                modified_at=_dt(item.get("modified_at")),
                observed_at=_dt(item.get("observed_at")) or utcnow(),
                topics=item.get("topics") or [],
                language=item.get("language"),
                region=item.get("region"),
                capture_hash=item["capture_hash"],
                raw_sha256=item.get("raw_sha256"),
                text_chars=item.get("text_chars"),
                excerpt=item.get("excerpt"),
                fetch_mode=item.get("fetch_mode", "http"),
                http_status=item.get("http_status"),
                content_type=item.get("content_type"),
                etag=item.get("etag"),
                http_last_modified=item.get("http_last_modified"),
                extractor=item.get("extractor"),
                snapshot_path=item.get("snapshot_path"),
                is_candidate=item.get("is_candidate", False),
                validation_status=item.get("validation_status", "validated"),
            )
        )
        created += 1
    return created


def store_statuses(session: Session, statuses: list[dict]) -> None:
    now = utcnow()
    for status in statuses:
        source = session.get(Source, status.get("source_id"))
        if source is None:
            continue
        state = status.get("status", "error")
        source.health_status = state
        source.last_check_at = now
        source.last_http_status = status.get("http_status")
        if state == "ok":
            source.last_success_at = now
            source.consecutive_failures = 0
            source.last_error = None
        else:
            source.consecutive_failures += 1
            source.last_error = status.get("error")
        session.add(
            SourceCheck(
                source_id=source.id,
                checked_at=now,
                status=state,
                http_status=status.get("http_status"),
                items_new=status.get("items_new", 0),
                content_changed=status.get("content_changed", False),
                error=status.get("error"),
            )
        )


def store_candidates(session: Session, candidates: list[dict], registered_hosts: set[str]) -> int:
    hits = [
        DiscoveryHit(
            title=c.get("title") or "",
            url=c["url"],
            canonical_url=c["canonical_url"],
            published_at=_dt(c.get("published_at")),
            provider=c.get("provider", "unknown"),
            query=c.get("query", ""),
            domain=c.get("host"),
        )
        for c in candidates
    ]
    created = record_candidates(
        session,
        hits,
        registered_hosts=registered_hosts,
        class_hint=candidates[0].get("source_class_guess") if candidates else None,
        topics=candidates[0].get("topics") if candidates else None,
    )
    return len(created)
