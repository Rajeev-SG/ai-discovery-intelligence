"""Executive brief: confidence scoring, significance scoring, brief generation.

Confidence and significance are separate axes. Confidence is derived from
source/methodology/sample/recency/geography/corroboration; significance from
reach/intent/magnitude/breadth/persistence/actionability. Neither uses LLM
self-reported confidence.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    LOW = "low"
    UNRESOLVED = "unresolved"


class ConfidenceScorer(BaseModel):
    """Weighted-input confidence scorer driven by config/significance.yaml."""

    source_authority: float = 0.2
    methodology_transparency: float = 0.15
    sample_strength: float = 0.15
    recency: float = 0.1
    geography_fit: float = 0.1
    corroboration: float = 0.2
    directness: float = 0.1

    def score(
        self,
        *,
        source_authority: float = 0.5,
        methodology_transparency: float = 0.5,
        sample_strength: float = 0.5,
        recency: float = 0.5,
        geography_fit: float = 0.5,
        corroboration: float = 0.5,
        directness: float = 0.5,
    ) -> float:
        return round(
            source_authority * self.source_authority
            + methodology_transparency * self.methodology_transparency
            + sample_strength * self.sample_strength
            + recency * self.recency
            + geography_fit * self.geography_fit
            + corroboration * self.corroboration
            + directness * self.directness,
            4,
        )

    def label(self, score: float) -> ConfidenceLabel:
        if score >= 0.85:
            return ConfidenceLabel.HIGH
        if score >= 0.70:
            return ConfidenceLabel.MEDIUM_HIGH
        if score >= 0.55:
            return ConfidenceLabel.MEDIUM
        if score > 0.0:
            return ConfidenceLabel.LOW
        return ConfidenceLabel.UNRESOLVED


class SignificanceScorer(BaseModel):
    """Weighted-input significance scorer driven by config/significance.yaml."""

    reach: float = 0.2
    commercial_intent: float = 0.2
    magnitude: float = 0.2
    breadth: float = 0.15
    persistence: float = 0.1
    actionability: float = 0.15

    def score(
        self,
        *,
        reach: float = 0.5,
        commercial_intent: float = 0.5,
        magnitude: float = 0.5,
        breadth: float = 0.5,
        persistence: float = 0.5,
        actionability: float = 0.5,
    ) -> float:
        raw = (
            reach * self.reach
            + commercial_intent * self.commercial_intent
            + magnitude * self.magnitude
            + breadth * self.breadth
            + persistence * self.persistence
            + actionability * self.actionability
        )
        # config says scale [0,5]; our weighted inputs are [0,1] so map to 0–5.
        return round(raw * 5.0, 2)


class BriefItem(BaseModel):
    """One executive-brief item (≤5 total; 0 valid)."""

    change: str
    why_it_matters: str
    agency_action: str
    confidence: ConfidenceLabel
    significance: float
    evidence_ids: list[str] = Field(default_factory=list)
    surfaces: list[str] = Field(default_factory=list)
    is_watch_item: bool = False


class BriefGenerator:
    """Generates a restrained weekly brief from scored candidates."""

    def __init__(
        self,
        *,
        confidence_scorer: ConfidenceScorer | None = None,
        significance_scorer: SignificanceScorer | None = None,
        max_items: int = 5,
        target_items: int = 3,
        min_confidence: ConfidenceLabel = ConfidenceLabel.MEDIUM,
        normal_min_significance: float = 3.5,
        watch_item_min_significance: float = 4.5,
    ):
        self.confidence_scorer = confidence_scorer or ConfidenceScorer()
        self.significance_scorer = significance_scorer or SignificanceScorer()
        self.max_items = max_items
        self.target_items = target_items
        self.min_confidence = min_confidence
        self.normal_min_significance = normal_min_significance
        self.watch_item_min_significance = watch_item_min_significance

    _confidence_rank = {
        ConfidenceLabel.HIGH: 4,
        ConfidenceLabel.MEDIUM_HIGH: 3,
        ConfidenceLabel.MEDIUM: 2,
        ConfidenceLabel.LOW: 1,
        ConfidenceLabel.UNRESOLVED: 0,
    }

    def generate(self, candidates: list[BriefItem]) -> list[BriefItem]:
        """Filter + sort + cap. High-noise/low-significance items are excluded."""
        min_rank = self._confidence_rank[self.min_confidence]
        included: list[BriefItem] = []
        for c in sorted(candidates, key=lambda x: -x.significance):
            rank = self._confidence_rank[c.confidence]
            if c.is_watch_item:
                # Watch items need ≥ watch_item_min_significance but can have lower confidence.
                if c.significance >= self.watch_item_min_significance:
                    included.append(c)
                continue
            if rank < min_rank:
                continue
            if c.significance >= self.normal_min_significance:
                included.append(c)
            if len(included) >= self.target_items:
                break
        return included[: self.max_items]
