"""Discovery-lane domain logic.

Candidates come from the direct discovery lane (crawler.run_discovery_jobs via
provider parsing in spiders_parse.py); this module only maps hits into the
canonical candidate table and deduplicates by canonical URL.
Candidates stay non-canonical until a human/validation step promotes them.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters.gdelt import DiscoveryHit
from .hashing import candidate_id, host_of
from .models import DiscoveredCandidate, utcnow


def record_candidates(
    session: Session,
    hits: list[DiscoveryHit],
    *,
    registered_hosts: set[str],
    class_hint: str | None = None,
    topics: list[str] | None = None,
) -> list[DiscoveredCandidate]:
    stored: list[DiscoveredCandidate] = []
    for hit in hits:
        cid = candidate_id(hit.canonical_url)
        existing = session.get(DiscoveredCandidate, cid)
        in_registry = host_of(hit.url) in registered_hosts
        if existing is None:
            candidate = DiscoveredCandidate(
                id=cid,
                url=hit.url,
                canonical_url=hit.canonical_url,
                host=host_of(hit.url),
                title=hit.title,
                discovered_via=hit.provider,
                discovery_query=hit.query,
                topics=topics or [],
                source_class_guess=class_hint,
                in_registry=in_registry,
                validation_status="validated" if in_registry else "unvalidated",
                first_seen_at=utcnow(),
                last_seen_at=utcnow(),
            )
            session.add(candidate)
            stored.append(candidate)
        else:
            existing.last_seen_at = utcnow()
            existing.in_registry = existing.in_registry or in_registry
    return stored


def candidate_urls(session: Session, *, limit: int = 5) -> list[DiscoveredCandidate]:
    """Newest non-registry candidates still awaiting validation."""
    return list(
        session.scalars(
            select(DiscoveredCandidate)
            .where(
                DiscoveredCandidate.in_registry.is_(False),
                DiscoveredCandidate.validation_status == "unvalidated",
            )
            .order_by(DiscoveredCandidate.first_seen_at.desc())
            .limit(limit)
        ).all()
    )
