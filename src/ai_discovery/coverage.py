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
    importance_score: float = Field(ge=0.0, le=1.0)
    evidence_available: bool = False
    existing_evidence_urls: list[str] = Field(default_factory=list)
    last_verified: dt.datetime | None = None
    stale_after_days: int | None = None
    suggested_research_query: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerDerivedMatrix:
    """Derive CoverageGap objects from the claim ledger + surface registry."""

    def __init__(
        self,
        claims: list,
        *,
        surfaces_registry: list[str] | None = None,
        stale_after_days: int = 90,
        now: dt.datetime | None = None,
        importance_overrides: dict[str, float] | None = None,
    ):
        self.claims = claims
        self.surfaces_registry = surfaces_registry or []
        self.stale_after_days = stale_after_days
        self.now = now or dt.datetime.now(dt.UTC)
        self.importance_overrides = importance_overrides or {}

    def derive(self) -> list[CoverageGap]:
        triples: dict[tuple[str, str, str], list] = {}
        for c in self.claims:
            for surface in getattr(c, "surfaces", [getattr(c, "surface", "")]):
                for topic in getattr(c, "topics", [getattr(c, "topic", "")]):
                    for geo in getattr(c, "geographies", [getattr(c, "geography", "global")]):
                        triples.setdefault((surface, topic, geo), []).append(c)

        # Registry surfaces with zero claims → no_evidence.
        registry_surfaces = set(self.surfaces_registry)
        known_claim_surfaces = {s for (s, _, _) in triples}
        for s in registry_surfaces - known_claim_surfaces:
            triples.setdefault((s, "retrieval", "global"), [])

        gaps = []
        for (surface, topic, geo), matched in triples.items():
            fresh = [c for c in matched if self._is_fresh(c)]
            stale = [c for c in matched if not self._is_fresh(c)]
            stale_urls = [getattr(c, "url", "") for c in stale if hasattr(c, "url")]
            if len(matched) == 0:
                gaps.append(self._gap_for(surface, topic, geo, GapCategory.no_evidence, []))
            elif len(fresh) == 0:
                gaps.append(
                    self._gap_for(
                        surface,
                        topic,
                        geo,
                        GapCategory.stale_evidence,
                        matched,
                        stale_urls=stale_urls,
                    )
                )
            elif len(fresh) == 1:
                gaps.append(
                    self._gap_for(
                        surface, topic, geo, GapCategory.single_source, fresh, stale_urls=stale_urls
                    )
                )
            else:
                continue
        return gaps

    def _is_fresh(self, claim) -> bool:
        observed = getattr(claim, "observed_at", None)
        if observed is None:
            return False
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=dt.UTC)
        return (self.now - observed).days <= self.stale_after_days

    def _gap_for(
        self,
        surface: str,
        topic: str,
        geo: str,
        category: GapCategory,
        claims: list,
        *,
        stale_urls: list[str] | None = None,
    ) -> CoverageGap:
        importance = self.importance_overrides.get(surface, 0.5)
        priority = (
            Priority.high
            if importance >= 0.75
            else Priority.medium
            if importance >= 0.5
            else Priority.low
        )
        return CoverageGap(
            id=f"gap-{surface}-{topic}-{geo}",
            surfaces=[surface],
            topics=[topic],
            geographies=[geo],
            category=category,
            description=f"{category.value} for {surface} × {topic} × {geo}",
            priority=priority,
            importance_score=importance,
            evidence_available=len(claims) > 0,
            existing_evidence_urls=[getattr(c, "url", "") for c in claims if hasattr(c, "url")],
            last_verified=getattr(claims[0], "observed_at", None) if claims else None,
            stale_after_days=self.stale_after_days,
            metadata={"stale_evidence_urls": stale_urls or []},
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
        order = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
        return sorted(self.gaps, key=lambda g: (order[g.priority], -g.importance_score, g.id))

    def is_stale(self, gap: CoverageGap, now: dt.datetime | None = None) -> bool:
        if gap.stale_after_days is None or gap.last_verified is None:
            return False
        reference = now or dt.datetime.now(dt.UTC)
        return (reference - gap.last_verified).days > gap.stale_after_days
