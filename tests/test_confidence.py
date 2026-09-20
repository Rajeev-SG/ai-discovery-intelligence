"""Confidence integrity (issue #28A): the label is derived, never asserted."""

from __future__ import annotations

from test_claims import _spec, _synthetic_capture

from ai_discovery import claims as C
from ai_discovery.confidence import assess_confidence, confidence_from_inputs


def test_model_saying_high_does_not_make_weak_evidence_high():
    """The headline 28A invariant.

    A spec (or LLM) proposing ``confidence: high`` must not raise the derived
    label. The spec label is recorded for audit only.
    """

    spec = _spec()
    spec["source"]["source_class"] = "other"  # weakest authority
    spec["confidence"] = "high"  # the model/spec asserting confidence
    # Strip the evidence that would justify confidence.
    spec["metrics"][0]["value"] = {"value": "1.2M", "quote": "1.2M monthly visits in January 2026"}
    spec["methodology"] = {"measurement_mode": "vendor_estimate"}
    spec["dates"]["published_at"] = None
    spec["dates"]["published_at_selector"] = None

    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.confidence in ("low", "unknown"), record.confidence
    assert record.confidence != "high"

    assessment = assess_confidence(record, model_asserted="high")
    assert assessment.model_asserted == "high"
    assert assessment.label != "high"
    assert assessment.label in ("low", "unresolved")


def test_strong_evidence_and_a_model_saying_low_still_scores_high():
    """The complement: evidence drives the label, not the asserted one."""

    spec = _spec()
    spec["source"]["source_class"] = "official"
    spec["confidence"] = "low"
    # Fully described methodology + verbatim-quoted values.
    spec["methodology"] = {
        "measurement_mode": "vendor_estimate",
        "metric_family": {"value": "visits", "quote": "monthly visits"},
        "metric_definition": {"value": "monthly visits", "quote": "1.2M monthly visits"},
        "denominator": {"value": "all visits", "quote": "1.2M monthly visits"},
        "unit_of_analysis": {"value": "visit", "quote": "monthly visits"},
        "time_window": {"value": "Jan 2026", "quote": "January 2026"},
        "geography": {"value": "US", "quote": "Widget Search"},
        "geography_basis": "source_stated",
        "language": {"value": "English", "quote": "Widget Search"},
        "language_basis": "source_stated",
        "sample_size": {"value": "12 months", "quote": "January 2026"},
    }
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    # Corroboration is a corpus-level input, so it is applied where the corpus is
    # known (the brief pipeline), not at single-claim extraction.
    assessment = assess_confidence(record, corroborating_sources=2, model_asserted="low")
    assert assessment.label == "high", (assessment.label, assessment.inputs)
    # The spec's asserted "low" never lowers the derived label either.
    assert record.confidence != "low"


def test_confidence_inputs_are_persisted_and_explain_the_label():
    """The label must be reproducible from persisted inputs (issue #28A)."""

    spec = _spec()
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.confidence_inputs, "scorer inputs must be persisted"
    assert record.confidence_rationale
    assert record.confidence_score is not None

    engine = C.create_ledger_engine("sqlite+pysqlite:///:memory:")
    C.init_ledger(engine)
    C.persist_claim(engine, record)

    row = C.load_expanded_claims(engine)[0]
    detail = row["confidence_detail"]
    assert detail["derived"] is True
    assert detail["inputs"] == record.confidence_inputs
    assert detail["score"] == record.confidence_score

    # Recomputing from the persisted inputs reproduces the same label.
    recomputed = confidence_from_inputs(detail["inputs"])
    assert recomputed.label in ("high", "medium_high", "medium", "low", "unresolved")
    assert recomputed.score == detail["score"]


def test_spec_label_alone_cannot_set_a_high_label():
    """No evidenced inputs -> an asserted 'high' still yields the weakest label."""

    spec = _spec()
    spec["source"]["source_class"] = "other"
    spec["confidence"] = "high"
    spec["methodology"] = {"measurement_mode": "unknown"}
    spec["metrics"][0]["value"] = {
        "value": "1.2M",
        "kind": "jsonld_field",
        "selector": "datePublished",
    }
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.confidence != "high"


# --------------------------------------------------------------------------- #
# Issue #58 DELTA-1/DELTA-2: the persisted-row explainer must match the record
# path exactly, and any label/rationale divergence must be surfaced, not hidden.
# --------------------------------------------------------------------------- #


def _row_from_record(record) -> dict:
    """A persisted-row shape (flat methodology) from a real ClaimRecord."""

    return {
        "claim_id": record.claim_id,
        "topic": record.topic,
        "statement": record.statement,
        "surfaces": record.surfaces,
        "status": record.status,
        "relationship": record.relationship,
        "confidence": record.confidence,
        "confidence_detail": {
            "score": record.confidence_score,
            "inputs": record.confidence_inputs,
            "rationale": record.confidence_rationale,
            "derived": True,
        },
        "source": {
            "source_id": record.source_id,
            "publisher": record.evidence.publisher,
            "url": record.evidence.url,
            "source_class": record.evidence.source_class,
        },
        "dates": {
            "published_at": (
                record.dates.published_at.value.isoformat()
                if record.dates.published_at.value
                else None
            ),
            "observed_at": record.dates.observed_at.isoformat()
            if record.dates.observed_at
            else None,
        },
        "methodology": {
            "measurement_mode": record.methodology.measurement_mode,
            "metric_family": record.methodology.metric_family.value,
            "denominator": record.methodology.denominator.value,
            "prompt_universe": record.methodology.prompt_universe.value,
            "sample_size": (
                str(record.methodology.sample_size.value)
                if record.methodology.sample_size.known
                else None
            ),
            "unit_of_analysis": record.methodology.unit_of_analysis.value,
            "time_window": record.methodology.time_window.value,
            "geography": record.methodology.geography.value,
            "geography_basis": record.methodology.geography_basis,
            "language": record.methodology.language.value,
            "language_basis": record.methodology.language_basis,
        },
        # Only metric-value locators count for directness, mirroring the record path.
        "metrics": [
            {
                "metric_id": m.metric_id,
                "label": m.label,
                "value_number": m.value.value if isinstance(m.value.value, (int, float)) else None,
                "unit": m.unit.value,
            }
            for m in record.metrics
        ],
        "provenance": [
            {
                "field_path": path,
                "locator_kind": loc.kind,
                "quote": loc.quote,
            }
            for path, loc in record.field_locators()
        ],
    }


def test_persisted_explainer_matches_record_path_inputs_and_rationale():
    """Review DELTA-2: for the same evidence, ``explain_persisted_confidence`` and
    ``assess_confidence`` must produce identical inputs and rationale lines."""

    from test_claims import _spec, _synthetic_capture

    from ai_discovery import claims as C
    from ai_discovery.confidence import assess_confidence, explain_persisted_confidence

    record = C.with_derived_confidence(
        C.extract_claim(spec=_spec(), capture=_synthetic_capture())
    )
    record_assessment = assess_confidence(record)
    row_assessment = explain_persisted_confidence(_row_from_record(record))

    assert row_assessment.inputs == record_assessment.inputs, (
        f"inputs diverged: row={row_assessment.inputs} record={record_assessment.inputs}"
    )
    assert row_assessment.rationale == record_assessment.rationale, (
        f"rationale diverged:\nrow={row_assessment.rationale}\nrecord={record_assessment.rationale}"
    )


def test_metric_less_claim_directness_matches_the_record_path():
    """Review DELTA-2(b): a claim with no metrics must read 0.5 "no metric values"
    on both paths, never a false 0.0 from a max(len,1) floor."""

    from ai_discovery.confidence import _directness_score

    # Row path: no metrics -> total_metrics 0.
    row = {"metrics": [], "provenance": [], "methodology": {}, "source": {}, "dates": {}}
    from ai_discovery.confidence import explain_persisted_confidence

    row_assessment = explain_persisted_confidence(row)
    record_value, record_why = _directness_score(0, 0)
    assert row_assessment.inputs["directness"] == record_value == 0.5
    assert row_assessment.rationale[5] == f"directness: {record_why}"


def test_non_metric_quote_does_not_inflate_directness():
    """Review DELTA-2(c): a non-metric verbatim quote must not count as a metric
    quote (the record path counts only metric-value locators)."""

    from ai_discovery.confidence import explain_persisted_confidence

    row = {
        "metrics": [{"metric_id": "m1", "label": "L", "value_number": 1.0, "unit": "%"}],
        "methodology": {},
        "source": {"source_class": "official"},
        "dates": {},
        # One metric locator quoted, one non-metric locator quoted.
        "provenance": [
            {"field_path": "metrics[0].value", "locator_kind": "verbatim_quote", "quote": "q"},
            {"field_path": "dates.published_at", "locator_kind": "verbatim_quote", "quote": "q"},
        ],
    }
    assessment = explain_persisted_confidence(row)
    # 1 of 1 metrics quoted -> directness 1.0, not 2/1.
    assert assessment.inputs["directness"] == 1.0
