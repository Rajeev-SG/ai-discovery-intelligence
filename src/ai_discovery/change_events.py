"""Append-only typed change events linked to claims and surfaces.

Event types follow docs/PIPELINES.md: product launch, retrieval_or_index_change,
audience_shift, citation_source_shift, crawler_policy, commerce_ads,
referral_measurement, correction_retraction.
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    product_launch = "product_launch"
    retrieval_or_index_change = "retrieval_or_index_change"
    audience_shift = "audience_shift"
    citation_source_shift = "citation_source_shift"
    crawler_policy = "crawler_policy"
    commerce_ads = "commerce_ads"
    referral_measurement = "referral_measurement"
    correction_retraction = "correction_retraction"


class ChangeEvent(BaseModel):
    """A dated, typed change with provenance. Immutable once created."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: EventType
    title: str
    description: str
    surfaces: list[str] = Field(default_factory=list)
    claims: list[str] = Field(
        default_factory=list, description="Claim IDs this event is grounded in"
    )
    evidence_urls: list[str] = Field(default_factory=list)
    observed_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    published_at: dt.datetime | None = None
    effective_from: dt.datetime | None = None
    supersedes: str | None = Field(
        default=None, description="Event ID this event updates/qualifies"
    )
    source_hash: str | None = Field(default=None, description="sha256 of the capture text")
    dedupe_key: str | None = Field(
        default=None, description="Stable key for syndicated/duplicate coverage"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True  # append-only: no in-place mutation


class EventStore:
    """In-memory append-only event store (production: DB-backed via SQLAlchemy)."""

    def __init__(self):
        self._events: dict[str, ChangeEvent] = {}

    def append(self, event: ChangeEvent) -> ChangeEvent:
        if event.id in self._events:
            raise ValueError(f"duplicate event id {event.id}")
        self._events[event.id] = event
        return event

    def get(self, event_id: str) -> ChangeEvent | None:
        return self._events.get(event_id)

    def all(self) -> list[ChangeEvent]:
        return list(self._events.values())

    def by_surface(self, surface_id: str) -> list[ChangeEvent]:
        return sorted(
            [e for e in self._events.values() if surface_id in e.surfaces],
            key=lambda e: e.published_at or e.observed_at,
        )

    def by_type(self, event_type: EventType) -> list[ChangeEvent]:
        return sorted(
            [e for e in self._events.values() if e.event_type == event_type],
            key=lambda e: e.published_at or e.observed_at,
        )

    def dedupe(self) -> list[ChangeEvent]:
        """Remove events with the same dedupe_key (keep the earliest)."""
        seen: set[str] = set()
        result: list[ChangeEvent] = []
        for event in sorted(self._events.values(), key=lambda e: e.published_at or e.observed_at):
            key = event.dedupe_key
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            result.append(event)
        return result

    def timeline(self, surface_id: str | None = None) -> list[ChangeEvent]:
        """Chronological timeline (optionally per-surface), deduplicated."""
        source = self.dedupe()
        if surface_id:
            return [e for e in source if surface_id in e.surfaces]
        return source
