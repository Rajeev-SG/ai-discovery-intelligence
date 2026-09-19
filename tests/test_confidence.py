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
