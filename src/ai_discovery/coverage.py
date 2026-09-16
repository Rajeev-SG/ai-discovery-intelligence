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
