"""Deterministic claim → change-event derivation (issue #5, wired for #9).

The acquisition lane persists a validated, human-reviewed claim when it captures
a genuine change in the evidence corpus. This module turns each such claim into
one typed, append-only change event linked to the claim and its surfaces — the
``claims → change_events`` step of the declared pipeline
(``docs/PIPELINES.md``).

No model is involved: the topic→event-type mapping is fixed, and the event's
effective time is the claim's publisher-stated publication date when the source
gave one, else it stays unset (an undated assertion is not a dated change). The
event id is derived from the claim id, so re-running the lane is idempotent: the
same claim re-extracted from the same source yields the same event.
"""

from __future__ import annotations

import datetime as dt

from .change_events import ChangeEvent, EventType
from .claim_models import ClaimRecord
from .observations import persist_events

# Claim topic → change-event type. Only topics that describe a market change map
# to an event; ``optimisation_implication`` is an implication, not a change, so
# it produces no event rather than a forced one.
TOPIC_TO_EVENT: dict[str, EventType] = {
    "audience_usage": EventType.audience_shift,
    "retrieval_index": EventType.retrieval_or_index_change,
    "citations_sources": EventType.citation_source_shift,
    "crawler_index_policy": EventType.crawler_policy,
    "commerce_ads": EventType.commerce_ads,
    "referrals_conversion": EventType.referral_measurement,
    "measurement": EventType.referral_measurement,
}

_MAX_TITLE = 160


def event_from_claim(claim: ClaimRecord) -> ChangeEvent | None:
    """One change event for one validated claim, or ``None`` if it is not a change."""

    event_type = TOPIC_TO_EVENT.get(claim.topic)
    if event_type is None:
        return None

    published = claim.dates.published_at.value
    published_at = (
        dt.datetime(published.year, published.month, published.day, tzinfo=dt.UTC)
        if published is not None
        else None
    )
    statement = claim.statement.strip()
    title = (
        statement if len(statement) <= _MAX_TITLE else statement[: _MAX_TITLE - 1].rstrip() + "…"
    )

    return ChangeEvent(
        id=claim.claim_id[:12],
        event_type=event_type,
        title=title,
        description=statement,
        surfaces=list(claim.surfaces),
        claims=[claim.claim_id],
        evidence_urls=[claim.evidence.canonical_url or claim.evidence.url],
        observed_at=claim.dates.observed_at,
        published_at=published_at,
        effective_from=published_at,
        source_hash=claim.evidence.capture_hash,
        dedupe_key=f"claim-{claim.claim_id}",
        metadata={
            "publisher": claim.evidence.publisher,
            "topic": claim.topic,
            "confidence": claim.confidence,
            "extraction_version": claim.extraction.version,
        },
    )


def events_from_claims(claims: list[ClaimRecord]) -> list[ChangeEvent]:
    """Derive the change events for a batch of validated claims (order-stable)."""

    events: list[ChangeEvent] = []
    for claim in claims:
        event = event_from_claim(claim)
        if event is not None:
            events.append(event)
    return events


def derive_and_persist(session, claims: list[ClaimRecord]) -> int:
    """Persist derived events on ``session`` (idempotent by claim-derived id)."""

    events = events_from_claims(claims)
    if not events:
        return 0
    return persist_events(session, events)
