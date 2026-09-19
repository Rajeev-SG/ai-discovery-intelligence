"""Executive brief: confidence scoring, significance scoring, brief generation.

Confidence and significance are separate axes. Confidence is derived from
source/methodology/sample/recency/geography/corroboration; significance from
reach/intent/magnitude/breadth/persistence/actionability. Neither uses LLM
self-reported confidence.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import BaseModel, Field


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    LOW = "low"
    UNRESOLVED = "unresolved"


class ConfidenceScorer(BaseModel):
    """Weighted-input confidence scorer. Weights loaded from config/significance.yaml."""

    source_authority: float = 0.2
    methodology_transparency: float = 0.15
    sample_strength: float = 0.15
    recency: float = 0.1
    geography_fit: float = 0.1
    corroboration: float = 0.2
    directness: float = 0.1

    @classmethod
    def from_config(cls, config_path: str | None = None) -> ConfidenceScorer:
        import os as _os

        _cfg_root = Path(
            _os.environ.get("AI_DISCOVERY_CONFIG_DIR", Path(__file__).resolve().parents[2] / "config")
        )
        path = Path(config_path or _cfg_root / "significance.yaml")
        cfg = yaml.safe_load(path.read_text())
        cd = cfg["confidence_dimensions"]
        return cls(
            source_authority=cd["source_authority"],
            methodology_transparency=cd["methodology_transparency"],
            sample_strength=cd["sample_strength"],
            recency=cd["recency"],
            geography_fit=cd["geography_fit"],
            corroboration=cd["corroboration"],
            directness=cd["directness"],
        )

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
    """Weighted-input significance scorer. Weights loaded from config/significance.yaml."""

    reach: float = 0.2
    commercial_intent: float = 0.2
    magnitude: float = 0.2
    breadth: float = 0.15
    persistence: float = 0.1
    actionability: float = 0.15

    @classmethod
    def from_config(cls, config_path: str | None = None) -> SignificanceScorer:
        path = Path(
            config_path or Path(__file__).resolve().parents[2] / "config" / "significance.yaml"
        )
        cfg = yaml.safe_load(path.read_text())
        dims = cfg["dimensions"]
        return cls(
            reach=dims["reach"],
            commercial_intent=dims["commercial_intent"],
            magnitude=dims["magnitude"],
            breadth=dims["breadth"],
            persistence=dims["persistence"],
            actionability=dims["actionability"],
        )

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
    # Event-time semantics (issue #27): when the change took hold / was announced,
    # distinct from ``observed_at`` (when we ingested it). A weekly brief reasons
    # over effective time, so an old study ingested this week is not "this week's
    # change".
    effective_from: dt.datetime | None = None
    published_at: dt.datetime | None = None
    observed_at: dt.datetime | None = None

    @property
    def effective_at(self) -> dt.datetime | None:
        """When the change happened: publisher-stated effective time, else publication."""

        return self.effective_from or self.published_at


# BriefGenerator resolves all thresholds from config/executive_policy.yaml via None sentinels.
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
        beyond_target_min_significance: float | None = None,
    ):
        if (
            max_items == 5
            and target_items == 3
            and min_confidence is ConfidenceLabel.MEDIUM
            and normal_min_significance == 3.5
            and watch_item_min_significance == 4.5
            and beyond_target_min_significance is None
        ):
            # Load defaults from config only when caller did not override any threshold.
            policy_path = Path(__file__).resolve().parents[2] / "config" / "executive_policy.yaml"
            if policy_path.exists():
                policy = yaml.safe_load(policy_path.read_text())["weekly_brief"]
                max_items = policy.get("hard_max_items", max_items)
                target_items = policy.get("target_items", target_items)
                mc = policy.get("minimum_confidence")
                if mc:
                    min_confidence = ConfidenceLabel(mc)
                normal_min_significance = policy.get(
                    "normal_minimum_significance", normal_min_significance
                )
                watch_item_min_significance = policy.get(
                    "watch_item_minimum_significance", watch_item_min_significance
                )
                beyond_target_min_significance = policy.get(
                    "beyond_target_minimum_significance", beyond_target_min_significance
                )
        self.confidence_scorer = confidence_scorer or ConfidenceScorer.from_config()
        self.significance_scorer = significance_scorer or SignificanceScorer.from_config()
        self.max_items = max_items
        self.target_items = target_items
        self.min_confidence = min_confidence
        self.normal_min_significance = normal_min_significance
        self.watch_item_min_significance = watch_item_min_significance
        # A soft target needs a stricter bar past the target; default to a full
        # point above the normal bar so weak extras cannot pad the brief.
        self.beyond_target_min_significance = (
            beyond_target_min_significance
            if beyond_target_min_significance is not None
            else normal_min_significance + 1.0
        )

    _confidence_rank: ClassVar[dict[ConfidenceLabel, int]] = {
        ConfidenceLabel.HIGH: 4,
        ConfidenceLabel.MEDIUM_HIGH: 3,
        ConfidenceLabel.MEDIUM: 2,
        ConfidenceLabel.LOW: 1,
        ConfidenceLabel.UNRESOLVED: 0,
    }

    def generate(
        self,
        candidates: list[BriefItem],
        *,
        window_start: dt.datetime | None = None,
        window_end: dt.datetime | None = None,
    ) -> list[BriefItem]:
        """Filter + rank + cap with soft-target / hard-max and watch-item semantics.

        When a window is supplied, an item is only considered when its *effective*
        time (``effective_from`` or ``published_at``) falls inside it. An item with
        no effective time is excluded from a windowed brief: we cannot assert it is
        this week's change, and first-ingesting an old study is not a market change.
        

        * ``max_items`` is the hard ceiling; nothing may exceed it.
        * ``target_items`` is a soft target, not a cap: the brief aims for it, but
          emits more (up to ``max_items``) when more material clears the bar, so a
          configured hard maximum is reachable instead of being dead config.
        * at most one watch item is admitted;
        * a watch item never displaces corroborated material — corroborated items
          are selected first, and a watch item only fills a slot that is still free
          below ``max_items``.
        """

        candidates = _apply_window(candidates, window_start, window_end)

        min_rank = self._confidence_rank[self.min_confidence]

        qualifying = sorted(
            (
                c
                for c in candidates
                if not c.is_watch_item
                and self._confidence_rank[c.confidence] >= min_rank
                and c.significance >= self.normal_min_significance
            ),
            key=lambda x: -x.significance,
        )

        # ``target_items`` is a soft target, not a cap: the first ``target_items``
        # slots admit anything clearing the normal bar, and any slot beyond it must
        # clear a stricter bar (``beyond_target_min_significance``). So the soft
        # target governs *quality* past the target rather than being dead config,
        # and the brief extends to ``max_items`` only for genuinely stronger items.
        beyond_bar = self.beyond_target_min_significance
        included: list[BriefItem] = []
        for c in qualifying:
            if len(included) >= self.max_items:
                break
            if len(included) >= self.target_items and c.significance < beyond_bar:
                continue  # not strong enough to extend past the soft target
            included.append(c)

        # A watch item is uncorroborated by definition: it may only use a slot no
        # corroborated item wanted, and only one may appear in a brief.
        if len(included) < self.max_items:
            watch = next(
                (
                    c
                    for c in sorted(candidates, key=lambda x: -x.significance)
                    if c.is_watch_item and c.significance >= self.watch_item_min_significance
                ),
                None,
            )
            if watch is not None:
                included.append(watch)

        return included


def _apply_window(
    candidates: list[BriefItem],
    window_start: dt.datetime | None,
    window_end: dt.datetime | None,
) -> list[BriefItem]:
    """Keep only items whose effective time is inside ``[start, end]``.

    A no-window call is unchanged. A windowed call drops items with no effective
    time (an undated item cannot be claimed as this week's change).
    """

    if window_start is None and window_end is None:
        return candidates
    out: list[BriefItem] = []
    for item in candidates:
        effective = item.effective_at
        if effective is None:
            continue
        if effective.tzinfo is None:
            effective = effective.replace(tzinfo=dt.UTC)
        if window_start is not None and effective < window_start:
            continue
        if window_end is not None and effective > window_end:
            continue
        out.append(item)
    return out


def weekly_window(
    reference: dt.datetime | None = None,
    *,
    days: int = 7,
) -> tuple[dt.datetime, dt.datetime]:
    """The ``[start, end]`` event-time window for a weekly brief.

    ``reference`` is the run time (default: now, UTC). The window is the trailing
    ``days`` up to ``reference``. Callers pass this to ``generate`` so the brief
    reasons over when changes *happened*, not when we crawled the pages.
    """

    end = reference or dt.datetime.now(dt.UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=dt.UTC)
    return end - dt.timedelta(days=days), end


def build_weekly_brief(
    candidates: list[BriefItem],
    *,
    generator: BriefGenerator | None = None,
    reference: dt.datetime | None = None,
    days: int = 7,
) -> list[BriefItem]:
    """Build the weekly brief over an explicit event-time window.

    This is the product entry point: it always applies the window, so a study
    published long ago but first ingested this week cannot appear as this week's
    change. Use it instead of calling ``generate`` directly for weekly output.
    """

    bg = generator or BriefGenerator()
    start, end = weekly_window(reference, days=days)
    return bg.generate(candidates, window_start=start, window_end=end)
