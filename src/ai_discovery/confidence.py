"""Deterministic, evidence-derived claim confidence (issue #28A).

Product-facing confidence must be a function of auditable evidence inputs, never
of an LLM's or a spec's self-reported label. A model (or a spec author) saying
"high" must not be able to make weak evidence high-confidence.

This module derives every input from the :class:`ClaimRecord` itself —

* ``source_authority``     from the source class,
* ``methodology_transparency`` from how many methodology fields are known,
* ``sample_strength``      from whether a sample size is stated and how,
* ``recency``              from capture time versus publication,
* ``geography_fit``        from whether geography is stated,
* ``corroboration``        from independent sources reporting the same claim,
* ``directness``           from whether the value carries a verbatim quote,

— scores them with the configured weights, and returns the score, the label, the
exact inputs and a human-readable rationale, so the label can always be explained.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .claim_models import ClaimRecord

# A source class is a claim about how close the publisher is to the primary fact.
SOURCE_AUTHORITY: dict[str, float] = {
    "official": 1.0,
    "market_telemetry": 0.9,
    # Independent visibility/citation research and open research report a
    # methodology and are second only to official/market telemetry.
    "visibility_research": 0.75,
    "open_research": 0.75,
    "industry_report": 0.75,
    "vendor_research": 0.7,
    "editorial_discovery": 0.55,
    "news": 0.55,
    "press_release": 0.5,
    "vendor_blog": 0.45,
    # Discovery-only aggregators are never canonical, so they score lowest.
    "open_discovery": 0.3,
    # First-party controlled observation: directly observed behaviour, but a
    # narrow sample and no publisher methodology; between official and editorial.
    "controlled_observation": 0.6,
    "other": 0.3,
}

_METHODOLOGY_FIELDS = (
    "metric_family",
    "metric_definition",
    "denominator",
    "prompt_universe",
    "sample_size",
    "unit_of_analysis",
    "time_window",
    "geography",
    "language",
)


class ConfidenceAssessment(BaseModel):
    """A confidence label plus the evidence inputs that produced it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    score: float
    inputs: dict[str, float] = Field(default_factory=dict)
    rationale: list[str] = Field(default_factory=list)
    model_asserted: str | None = None  # any label the spec/model proposed; never authoritative


def _recency_score(record: ClaimRecord) -> tuple[float, str]:
    """How fresh the capture is relative to the study's publication."""

    observed = record.dates.observed_at
    published = record.dates.published_at.value
    if published is None:
        return 0.4, "publication date unknown"
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=dt.UTC)
    age_days = (observed.date() - published).days
    if age_days <= 30:
        return 1.0, f"captured {age_days}d after publication"
    if age_days <= 180:
        return 0.7, f"captured {age_days}d after publication"
    if age_days <= 365:
        return 0.4, f"captured {age_days}d after publication"
    return 0.2, f"captured {age_days}d after publication (stale)"


def _methodology_score(record: ClaimRecord) -> tuple[float, str]:
    known = sum(1 for f in _METHODOLOGY_FIELDS if getattr(record.methodology, f).known)
    score = round(known / len(_METHODOLOGY_FIELDS), 4)
    return score, f"{known}/{len(_METHODOLOGY_FIELDS)} methodology fields stated"


def _sample_score(record: ClaimRecord) -> tuple[float, str]:
    sample = record.methodology.sample_size
    if not sample.known:
        return 0.3, "no sample size stated"
    return 0.9, f"sample size stated: {sample.value}"


def _geography_score(record: ClaimRecord) -> tuple[float, str]:
    geo = record.methodology.geography
    if geo.known:
        return 0.9, f"geography stated: {geo.value}"
    if record.methodology.geography_basis not in ("not_stated", "", None):
        return 0.5, f"geography inferred ({record.methodology.geography_basis})"
    return 0.3, "geography not stated"


def _directness_score(record: ClaimRecord) -> tuple[float, str]:
    """A value backed by a verbatim quote is more direct than one via a selector."""

    quoted = 0
    total = 0
    for metric in record.metrics:
        total += 1
        if metric.value.locator and metric.value.locator.quote:
            quoted += 1
    if total == 0:
        return 0.5, "no metric values"
    score = round(quoted / total, 4)
    return score, f"{quoted}/{total} metric values carry a verbatim quote"


def _corroboration_score(corroborating_sources: int) -> tuple[float, str]:
    if corroborating_sources <= 0:
        return 0.3, "no independent corroborating source"
    if corroborating_sources == 1:
        return 0.7, "1 independent corroborating source"
    return 1.0, f"{corroborating_sources} independent corroborating sources"


def assess_confidence(
    record: ClaimRecord,
    *,
    corroborating_sources: int = 0,
    weights: dict[str, float] | None = None,
    model_asserted: str | None = None,
) -> ConfidenceAssessment:
    """Derive confidence from evidence inputs; never from a model's own label.

    ``model_asserted`` is recorded for audit only. It cannot raise (or lower) the
    label: the label is a pure function of the derived inputs.
    """

    from .brief import ConfidenceScorer

    scorer = ConfidenceScorer.from_config() if weights is None else ConfidenceScorer(**weights)

    rationale: list[str] = []
    inputs: dict[str, float] = {}

    inputs["source_authority"] = SOURCE_AUTHORITY.get(record.evidence.source_class, 0.3)
    rationale.append(f"source class {record.evidence.source_class}")

    for name, (value, why) in (
        ("methodology_transparency", _methodology_score(record)),
        ("sample_strength", _sample_score(record)),
        ("recency", _recency_score(record)),
        ("geography_fit", _geography_score(record)),
        ("directness", _directness_score(record)),
        ("corroboration", _corroboration_score(corroborating_sources)),
    ):
        inputs[name] = value
        rationale.append(f"{name}: {why}")

    score = scorer.score(**inputs)
    label = scorer.label(score)
    return ConfidenceAssessment(
        label=label.value,
        score=score,
        inputs=inputs,
        rationale=rationale,
        model_asserted=model_asserted,
    )


def confidence_from_inputs(inputs: dict[str, Any]) -> ConfidenceAssessment:
    """Recompute the label from persisted inputs, so a stored label is checkable."""

    from .brief import ConfidenceScorer

    scorer = ConfidenceScorer.from_config()
    clean = {k: float(v) for k, v in inputs.items()}
    score = scorer.score(**clean)
    return ConfidenceAssessment(label=scorer.label(score).value, score=score, inputs=clean)
