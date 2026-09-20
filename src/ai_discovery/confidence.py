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


def _recency_score(published_at: dt.date | None, observed_at: dt.datetime | None) -> tuple[float, str]:
    """How fresh the capture is relative to the study's publication."""

    if published_at is None:
        return 0.4, "publication date unknown"
    if observed_at is None:
        return 0.4, "observation time unknown"
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=dt.UTC)
    age_days = (observed_at.date() - published_at).days
    if age_days <= 30:
        return 1.0, f"captured {age_days}d after publication"
    if age_days <= 180:
        return 0.7, f"captured {age_days}d after publication"
    if age_days <= 365:
        return 0.4, f"captured {age_days}d after publication"
    return 0.2, f"captured {age_days}d after publication (stale)"


def _methodology_score(known: int, total: int) -> tuple[float, str]:
    return round(known / total, 4), f"{known}/{total} methodology fields stated"


def _sample_score(sample_value: object | None) -> tuple[float, str]:
    if sample_value is None:
        return 0.3, "no sample size stated"
    return 0.9, f"sample size stated: {sample_value}"


def _geography_score(geography: str | None, geography_basis: str | None) -> tuple[float, str]:
    if geography:
        return 0.9, f"geography stated: {geography}"
    if geography_basis not in ("not_stated", "", None):
        return 0.5, f"geography inferred ({geography_basis})"
    return 0.3, "geography not stated"


def _directness_score(quoted: int, total: int) -> tuple[float, str]:
    """A value backed by a verbatim quote is more direct than one via a selector."""

    if total == 0:
        return 0.5, "no metric values"
    return round(quoted / total, 4), f"{quoted}/{total} metric values carry a verbatim quote"


def _corroboration_score(corroborating_sources: int) -> tuple[float, str]:
    if corroborating_sources <= 0:
        return 0.3, "no independent corroborating source"
    if corroborating_sources == 1:
        return 0.7, "1 independent corroborating source"
    return 1.0, f"{corroborating_sources} independent corroborating sources"


def confidence_inputs(
    *,
    source_class: str,
    methodology_known: int,
    methodology_total: int,
    sample_value: object | None,
    geography: str | None,
    geography_basis: str | None,
    published_at: dt.date | None,
    observed_at: dt.datetime | None,
    quoted_metrics: int,
    total_metrics: int,
    corroborating_sources: int = 0,
    weights: dict[str, float] | None = None,
) -> ConfidenceAssessment:
    """The single confidence derivation (issue #58 review F5: one implementation).

    Takes primitives so both the record path (:func:`assess_confidence`) and the
    persisted-row explainer (:func:`explain_persisted_confidence`) call the same
    logic and produce identical inputs and rationale text. ``model_asserted`` is
    never consulted; the label is a pure function of the derived inputs.
    """

    from .brief import ConfidenceScorer

    scorer = ConfidenceScorer.from_config() if weights is None else ConfidenceScorer(**weights)

    rationale: list[str] = []
    inputs: dict[str, float] = {}

    inputs["source_authority"] = SOURCE_AUTHORITY.get(source_class, 0.3)
    rationale.append(f"source class {source_class}")

    for name, (value, why) in (
        ("methodology_transparency", _methodology_score(methodology_known, methodology_total)),
        ("sample_strength", _sample_score(sample_value)),
        ("recency", _recency_score(published_at, observed_at)),
        ("geography_fit", _geography_score(geography, geography_basis)),
        ("directness", _directness_score(quoted_metrics, total_metrics)),
        ("corroboration", _corroboration_score(corroborating_sources)),
    ):
        inputs[name] = value
        rationale.append(f"{name}: {why}")

    score = scorer.score(**inputs)
    return ConfidenceAssessment(label=scorer.label(score).value, score=score, inputs=inputs, rationale=rationale)


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

    methodology_known = sum(1 for f in _METHODOLOGY_FIELDS if getattr(record.methodology, f).known)
    sample = record.methodology.sample_size
    quoted = sum(1 for m in record.metrics if m.value.locator and m.value.locator.quote)
    assessment = confidence_inputs(
        source_class=record.evidence.source_class,
        methodology_known=methodology_known,
        methodology_total=len(_METHODOLOGY_FIELDS),
        sample_value=sample.value if sample.known else None,
        geography=record.methodology.geography.value,
        geography_basis=record.methodology.geography_basis,
        published_at=record.dates.published_at.value,
        observed_at=record.dates.observed_at,
        quoted_metrics=quoted,
        total_metrics=len(record.metrics),
        corroborating_sources=corroborating_sources,
        weights=weights,
    )
    return assessment.model_copy(update={"model_asserted": model_asserted})


def explain_persisted_confidence(row: dict[str, Any], *, corroborating_sources: int = 0) -> ConfidenceAssessment:
    """Derive inputs + rationale for an ALREADY-PERSISTED claim row.

    Reuses the one confidence implementation above so a claim captured before the
    LLM lane recorded its rationale (issue #58 review F4) can still explain its
    confidence at read time. The persisted ``confidence`` label is never changed
    here; the derived inputs are what the trust layer needs to state *why*.
    """

    methodology = row.get("methodology") or {}
    metrics = row.get("metrics") or []
    dates = row.get("dates") or {}
    source = row.get("source") or {}
    published = dates.get("published_at")
    observed = dates.get("observed_at")
    published_at = None
    if published:
        try:
            published_at = dt.date.fromisoformat(str(published)[:10])
        except ValueError:
            published_at = None
    observed_at = None
    if observed:
        try:
            observed_at = dt.datetime.fromisoformat(str(observed))
        except ValueError:
            observed_at = None
    methodology_known = sum(1 for f in _METHODOLOGY_FIELDS if methodology.get(f))
    quoted = sum(
        1
        for loc in (row.get("provenance") or [])
        if loc.get("locator_kind") == "verbatim_quote" and loc.get("quote")
    )
    # Count quoting only over metric-bearing locators, matching _directness_score
    # on the record path (metrics[..] locators).
    metric_quoted = sum(
        1
        for loc in (row.get("provenance") or [])
        if str(loc.get("field_path") or "").startswith("metrics[")
        and loc.get("locator_kind") == "verbatim_quote"
        and loc.get("quote")
    )
    return confidence_inputs(
        source_class=source.get("source_class") or "other",
        methodology_known=methodology_known,
        methodology_total=len(_METHODOLOGY_FIELDS),
        sample_value=methodology.get("sample_size"),
        geography=methodology.get("geography"),
        geography_basis=methodology.get("geography_basis"),
        published_at=published_at,
        observed_at=observed_at,
        quoted_metrics=metric_quoted or quoted,
        total_metrics=max(len(metrics), 1),
        corroborating_sources=corroborating_sources,
    )


def confidence_from_inputs(inputs: dict[str, Any]) -> ConfidenceAssessment:
    """Recompute the label from persisted inputs, so a stored label is checkable."""

    from .brief import ConfidenceScorer

    scorer = ConfidenceScorer.from_config()
    clean = {k: float(v) for k, v in inputs.items()}
    score = scorer.score(**clean)
    return ConfidenceAssessment(label=scorer.label(score).value, score=score, inputs=clean)
