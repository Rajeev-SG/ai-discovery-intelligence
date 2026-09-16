"""Coverage-gap model: surface × topic × geography × freshness.

A gap means "no evidence exists (yet)", not "the source is down". Source
health/fetch failure is tracked separately (issue #2 does that in the
source_health table; this module is the analytical view).
"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GapCategory(str, Enum):
    no_evidence = "no_evidence"
    stale_evidence = "stale_evidence"
    single_source = "single_source"
    conflicting_evidence = "conflicting_evidence"
    under_documented = "under_documented"
    region_missing = "region_missing"
    fetch_failed = "fetch_failed"


class SourceHealth(BaseModel):
    """A fetch/health observation for one source. Tracked separately from evidence existence."""

    source_id: str
    last_attempt: dt.datetime | None = None
    status: str = "unknown"
    http_status: int | None = None
    error: str | None = None
    consecutive_failures: int = 0


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CoverageGap(BaseModel):
    """One identified gap, with the importance that drives research priority."""

    id: str
    surfaces: list[str]
    topics: list[str]
    geographies: list[str]
    category: GapCategory
    description: str
    priority: Priority
    importance_score: float = Field(
        ge=0.0, le=1.0, description="reach × commercial intent × magnitude"
    )
    evidence_available: bool = False
    existing_evidence_urls: list[str] = Field(default_factory=list)
    last_verified: dt.datetime | None = None
    stale_after_days: int | None = None
    suggested_research_query: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerDerivedMatrix:
    """Derive CoverageGap objects from the claim ledger, not a hardcoded list.

    For each (surface × topic × geography) triple, inspect ClaimRecord instances
    and classify: covered / stale / single_source / no_evidence / fetch_failed.
    """

    def __init__(self, claims: list, *, stale_after_days: int = 90, now: dt.datetime | None = None):
        self.claims = claims
        self.stale_after_days = stale_after_days
        self.now = now or dt.datetime.now(dt.UTC)

    def derive(self) -> list[CoverageGap]:
        """Build gaps from the claim ledger."""
        triples: dict[tuple[str, str, str], list] = {}
        for c in self.claims:
            for surface in getattr(c, "surfaces", [getattr(c, "surface", "")]):
                for topic in getattr(c, "topics", [getattr(c, "topic", "")]):
                    for geo in getattr(c, "geographies", [getattr(c, "geography", "global")]):
                        key = (surface, topic, geo)
                        triples.setdefault(key, []).append(c)
        gaps = []
        for (surface, topic, geo), matched in triples.items():
            fresh = [c for c in matched if self._is_fresh(c)]
            stale = [c for c in matched if not self._is_fresh(c)]
            if len(matched) == 0:
                continue
            elif len(fresh) == 0:
                gaps.append(self._gap_for(surface, topic, geo, GapCategory.stale_evidence, matched))
            elif len(fresh) == 1:
                gaps.append(self._gap_for(surface, topic, geo, GapCategory.single_source, fresh))
            else:
                continue  # covered: multiple fresh sources, no gap
        return gaps

    def _is_fresh(self, claim) -> bool:
        observed = getattr(claim, "observed_at", None) or getattr(claim, "published_at", None)
        if observed is None:
            return False
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=dt.UTC)
        return (self.now - observed).days <= self.stale_after_days

    def _gap_for(
        self, surface: str, topic: str, geo: str, category: GapCategory, claims: list
    ) -> CoverageGap:
        return CoverageGap(
            id=f"gap-{surface}-{topic}-{geo}",
            surfaces=[surface],
            topics=[topic],
            geographies=[geo],
            category=category,
            description=f"{category.value} for {surface} × {topic} × {geo}",
            priority=Priority.medium,
            importance_score=0.5,
            evidence_available=len(claims) > 0,
            existing_evidence_urls=[getattr(c, "url", "") for c in claims if hasattr(c, "url")],
            last_verified=getattr(claims[0], "observed_at", None)
            or getattr(claims[0], "published_at", None),
            stale_after_days=self.stale_after_days,
        )


class CoverageMatrix:
    """Analytical view over gaps: surface × topic × geography × freshness."""

    def __init__(self, gaps: list[CoverageGap]):
        self.gaps = gaps

    def by_priority(self, p: Priority) -> list[CoverageGap]:
        return [g for g in self.gaps if g.priority == p]

    def by_category(self, c: GapCategory) -> list[CoverageGap]:
        return [g for g in self.gaps if g.category == c]

    def for_surface(self, surface_id: str) -> list[CoverageGap]:
        return [g for g in self.gaps if surface_id in g.surfaces]

    def research_queue(self) -> list[CoverageGap]:
        """Prioritised next-research queue: high → medium → low, descending importance."""
        order = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
        return sorted(self.gaps, key=lambda g: (order[g.priority], -g.importance_score, g.id))

    def is_stale(self, gap: CoverageGap, now: dt.datetime | None = None) -> bool:
        if gap.stale_after_days is None or gap.last_verified is None:
            return False
        reference = now or dt.datetime.now(dt.UTC)
        return (reference - gap.last_verified).days > gap.stale_after_days
