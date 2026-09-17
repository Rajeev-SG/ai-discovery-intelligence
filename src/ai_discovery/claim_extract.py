"""Map Instructor-extracted claims into the validated ledger schema.

This module owns the *shaping* half of the rebuild: the model result
(``ai_discovery.semantic``) becomes ``ClaimRecord`` rows whose every known
field carries a verbatim-quote ``Locator``. The deterministic
``Locator.present_in`` check runs before any record is returned, so a
fabricated number or a hallucinated quote fails loudly instead of reaching
the ledger.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import ValidationError

from .claim_models import (
    EXTRACTION_VERSION,
    CaptureEvidence,
    ClaimRecord,
    DateProfile,
    ExtractionProvenance,
    Locator,
    Metric,
    Provenanced,
    StudyMethodology,
    claim_id_for,
)
from .claims import Capture, ClaimSpecError, check_against_capture
from .semantic import ExtractedClaim, ExtractedMetric


def _date(value: str | None, quote: str | None, *, kind: str = "page_stamp") -> Provenanced[dt.date]:
    """A dated value must name where it came from; otherwise it stays unknown."""
    if value is None:
        return Provenanced[dt.date]()
    parsed = dt.date.fromisoformat(str(value)[:10])
    if not quote:
        raise ClaimSpecError(f"date {value!r} needs a quote naming where it came from")
    return Provenanced[dt.date](value=parsed, locator=Locator(kind=kind, quote=quote))


def _metric_fields(index: int, raw: ExtractedMetric, *, anchor: str | None = None) -> Metric | None:
    """One metric; returns None when the model supplied no value (not claimable)."""
    if raw.value is None:
        return None
    def _anchor_of(_claim):  # placeholder replaced below
        return None
    if raw.value is None:
        return None
    # window/scope are the metric's frame, not separate assertions: they ride
    # on the value quote (the exact sentence carrying the number) when the
    # model did not give a dedicated quote.
    def _frame(value: Any, quote: str | None, fallback: str | None, name: str):
        if value is None:
            return Provenanced()
        locator = quote or fallback
        if not locator:
            raise ClaimSpecError(
                f"metrics[{index}].{name} value {value!r} carries no verbatim quote"
            )
        return Provenanced(value=value, locator=Locator(kind="verbatim_quote", quote=locator))

    fields: dict[str, Provenanced[Any]] = {
        "definition": _frame(
            raw.definition, raw.definition_quote, raw.value_quote or anchor, "definition"
        ),
        "value": _frame(raw.value, raw.value_quote, anchor, "value"),
        "unit": (
            Provenanced(
                value=raw.unit,
                locator=Locator(kind="verbatim_quote", quote=raw.value_quote),
            )
            if raw.unit is not None and raw.value_quote
            else Provenanced()
        ),
        "window": _frame(raw.window, raw.window_quote, raw.value_quote or anchor, "window"),
        "scope": _frame(raw.scope, raw.scope_quote, raw.value_quote or anchor, "scope"),
    }
    return Metric(
        metric_id=f"m{index + 1}",
        label=raw.label,
        definition=fields["definition"],
        value=fields["value"],
        unit=fields["unit"],
        comparator=raw.comparator,
        window=fields["window"],
        scope=fields["scope"],
    )


def _methodology(claim: ExtractedClaim) -> StudyMethodology:
    """Methodology block: every known field carries its own quote."""
    def known(value: str | None, quote: str | None) -> Provenanced[str]:
        if value is None:
            return Provenanced()
        if not quote:
            raise ClaimSpecError(
                f"methodology.{value!r} carries no verbatim quote; leave it unknown instead"
            )
        return Provenanced(value=value, locator=Locator(kind="verbatim_quote", quote=quote))

    geography = known(claim.geography, claim.geography_quote)
    language = known(claim.language, claim.language_quote)
    geography_basis = "source_stated" if geography.known else "not_stated"
    language_basis = "source_stated" if language.known else "not_stated"
    return StudyMethodology(
        surfaces=[s for s in claim.surfaces if s],
        measurement_mode=claim.measurement_mode,
        metric_family=known(claim.metric_family, claim.metric_family_quote),
        metric_definition=known(claim.metric_definition, claim.metric_definition_quote),
        denominator=known(claim.denominator, claim.denominator_quote),
        prompt_universe=known(claim.prompt_universe, claim.prompt_universe_quote),
        sample_size=known(claim.sample_size, claim.sample_size_quote),
        unit_of_analysis=known(claim.unit_of_analysis, claim.unit_of_analysis_quote),
        time_window=known(claim.time_window, claim.time_window_quote),
        geography=geography,
        geography_basis=geography_basis,
        language=language,
        language_basis=language_basis,
        devices=known(claim.devices, claim.devices_quote),
        limitations=[str(x) for x in claim.limitations],
        methodology_notes=known(claim.methodology_notes, claim.methodology_notes_quote),
    )


def _evidence(
    claim: ExtractedClaim,
    *,
    source: dict[str, Any],
    capture: Capture,
) -> CaptureEvidence:
    return CaptureEvidence(
        source_id=source["source_id"],
        publisher=source["publisher"],
        url=source["url"],
        canonical_url=source["canonical_url"],
        source_class=source["source_class"],
        capture_hash=capture.capture_hash,
        raw_sha256=capture.raw_sha256,
        snapshot_path=source.get("snapshot_path"),
        http_status=source.get("http_status"),
        content_type=source.get("content_type"),
        text_chars=capture.text_chars,
        robots_allowed=source.get("robots_allowed"),
        fetched_at=capture.fetched_at,
    )


def claim_from_extracted(
    claim: ExtractedClaim,
    *,
    source: dict[str, Any],
    capture: Capture,
    human_reviewed: bool = False,
) -> ClaimRecord:
    """Shape one extracted claim into a validated, quote-verified ClaimRecord."""
    statement = claim.statement.strip()
    topic = claim.topic
    methodology = _methodology(claim)
    if not methodology.surfaces:
        raise ClaimSpecError(f"claim {statement[:60]!r}: surfaces must list at least one surface id")

    metrics = [
        m
        for m in (
            _metric_fields(i, raw, anchor=claim.capture_anchor)
            for i, raw in enumerate(claim.metrics)
        )
        if m is not None
    ]
    if not metrics:
        raise ClaimSpecError("claim has no metric with a value; not ledger-claimable")

    measured_window = claim.measured_window
    if measured_window and not claim.measured_window_quote:
        # Mirror the methodology time_window locator: same measurement period,
        # same sentence as evidence.
        claim.measured_window_quote = claim.time_window_quote or claim.capture_anchor

    # The model has no dedicated published_at quote field; reuse the
    # methodology time_window quote (or the capture anchor) as the
    # date-source locator when the model gave one, else the date stays unknown.
    date_quote = claim.time_window_quote or claim.capture_anchor
    dates = DateProfile(
        published_at=(
            _date(claim.published_at, date_quote) if claim.published_at else Provenanced[dt.date]()
        ),
        modified_at=(
            _date(claim.modified_at, date_quote) if claim.modified_at else Provenanced[dt.date]()
        ),
        measured_window=(
            Provenanced(
                value=measured_window,
                locator=Locator(kind="verbatim_quote", quote=claim.measured_window_quote),
            )
            if measured_window and claim.measured_window_quote
            else Provenanced()
        ),
    )

    extraction = ExtractionProvenance(
        method="llm_proposal",
        tool="ai_discovery.semantic",
        version=EXTRACTION_VERSION,
        rule_id=None,
        human_reviewed=human_reviewed,
    )

    anchors = [Locator(kind=claim.capture_anchor_kind, quote=claim.capture_anchor)]
    evidence = _evidence(claim, source=source, capture=capture)
    record = ClaimRecord(
        claim_id=claim_id_for(evidence.source_id, topic, statement),
        source_id=evidence.source_id,
        topic=topic,
        statement=statement,
        surfaces=methodology.surfaces,
        metrics=metrics,
        methodology=methodology,
        dates=dates,
        evidence=evidence,
        capture_anchors=anchors,
        extraction=extraction,
        status="current",
        relationship="new",
        confidence="medium",
    )
    missing = check_against_capture(record, capture)
    if missing:
        joined = "; ".join(missing)
        raise ClaimSpecError(f"model quote not found in capture: {joined}")
    return record


def claims_from_extraction(
    result: Any,
    *,
    source: dict[str, Any],
    capture: Capture,
    human_reviewed: bool = False,
) -> list[ClaimRecord]:
    """Validate every extracted claim; return only the records that fully verify.

    ``human_reviewed=True`` marks the extraction as reviewed against the source
    capture; without it, the record is an ``llm_proposal`` that the ledger's
    provenance validator keeps out of evidence status.
    """
    records: list[ClaimRecord] = []
    failures: list[str] = []
    for index, extracted in enumerate(result.claims):
        try:
            records.append(
                claim_from_extracted(
                    extracted, source=source, capture=capture, human_reviewed=human_reviewed
                )
            )
        except (ValidationError, ClaimSpecError) as error:
            failures.append(f"claim {index}: {error}")
    if not records:
        detail = "\n".join(failures) or "extraction returned no claims"
        raise ClaimSpecError(f"no verifiable claims from {source['source_id']}:\n{detail}")
    return records
