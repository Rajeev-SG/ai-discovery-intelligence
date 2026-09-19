"""Rule-driven extraction against real captures, plus append-only ledger behaviour.

The real-capture tests read the verified public pages under ``/tmp/adi-cap``
(produced by the proof recipe) and skip when those captures are absent, so the
suite stays runnable offline. The synthetic tests below are the deterministic
negative controls; the real captures are acceptance evidence, never fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_discovery import claims as C

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / "proof" / "claim_ledger" / "claim_specs.json"
CAPTURE_DIR = Path("/tmp/adi-cap")
CAPTURE_FILES = {
    "similarweb-most-visited-websites": "sim.html",
    "sistrix-ai-citation-drift": "sis.html",
    "yandex-ai-search-pretrain-2026-09": "yan.html",
    "naver-ai-tab-launch-2026-06": "naver.html",
}

SYNTHETIC = """
<html><head><script type="application/ld+json">
{"datePublished":"2026-01-02T00:00:00+00:00","dateModified":"2026-01-03T00:00:00+00:00"}
</script></head><body>
<p>Widget Search had 1.2M monthly visits in January 2026.</p>
</body></html>
"""


def _synthetic_capture() -> C.Capture:
    return C.Capture(raw=SYNTHETIC.encode(), text=C.extract_capture_text(SYNTHETIC))


def _spec(**overrides):
    spec = {
        "source": {
            "source_id": "widget",
            "publisher": "Widget Inc",
            "url": "https://example.test/a",
            "canonical_url": "https://example.test/a",
            "source_class": "vendor_research",
        },
        "topic": "audience_usage",
        "statement": "Widget Search had 1.2M monthly visits in January 2026.",
        "surfaces": ["widget-search"],
        "methodology": {"measurement_mode": "vendor_estimate"},
        "metrics": [
            {
                "metric_id": "visits",
                "label": "Monthly visits",
                "definition": {"value": "monthly visits", "quote": "1.2M monthly visits"},
                "value": {"value": "1.2M", "quote": "1.2M monthly visits in January 2026"},
                "unit": {"value": "visits", "quote": "monthly visits"},
                "window": {"value": "Jan 2026", "quote": "in January 2026"},
                "scope": {"value": "Widget Search", "quote": "Widget Search"},
            }
        ],
        "dates": {
            "published_at": "2026-01-02",
            "published_at_selector": "datePublished",
            "modified_at": "2026-01-03",
            "modified_at_selector": "dateModified",
            "measured_window": {"value": "Jan 2026", "quote": "January 2026"},
            "observed_at": "2026-09-16T00:00:00+00:00",
        },
        "capture_anchors": [{"kind": "verbatim_quote", "quote": "1.2M monthly visits"}],
    }
    spec.update(overrides)
    return spec


# --- deterministic negative controls --------------------------------------- #


def test_a_supported_claim_extracts():
    record = C.extract_claim(spec=_spec(), capture=_synthetic_capture())
    assert record.topic == "audience_usage"
    assert record.metrics[0].value.value == "1.2M"
    assert len(record.field_locators()) >= 6


def test_a_fabricated_number_is_rejected():
    spec = _spec()
    spec["metrics"][0]["value"] = {"value": "9.9M", "quote": "9.9M monthly visits in January 2026"}
    with pytest.raises(C.ClaimSpecError, match="not found in capture"):
        C.extract_claim(spec=spec, capture=_synthetic_capture())


def test_a_value_without_a_locator_is_rejected():
    spec = _spec()
    spec["metrics"][0]["value"] = {"value": "1.2M"}  # no quote
    with pytest.raises(ValidationError):
        C.extract_claim(spec=spec, capture=_synthetic_capture())


def test_unsupported_optional_fields_stay_unknown():
    record = C.extract_claim(spec=_spec(), capture=_synthetic_capture())
    assert record.methodology.sample_size.known is False
    assert record.methodology.denominator.known is False
    assert record.dates.published_at.known and record.dates.modified_at.known


def test_llm_proposal_claim_is_blocked_without_human_review():
    spec = _spec(extraction={"method": "llm_proposal", "tool": "instructor", "version": "0.1"})
    with pytest.raises(ValidationError):
        C.extract_claim(spec=spec, capture=_synthetic_capture())
    spec["extraction"]["human_reviewed"] = True
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.extraction.human_reviewed


# --- append-only ledger ----------------------------------------------------- #


def test_ledger_is_append_only_and_expanded_view_is_complete():
    capture = _synthetic_capture()
    record = C.extract_claim(spec=_spec(), capture=capture)
    engine = C.create_ledger_engine("sqlite+pysqlite:///:memory:")
    C.init_ledger(engine)
    _, created = C.persist_claim(engine, record)
    assert created is True

    # Re-capture (page re-rendered): a new capture_hash appends evidence, the
    # original rows are untouched because nothing is ever UPDATEd in place.
    again = C.Capture(raw=capture.raw, text=capture.text + " [re-rendered 2026-09-16]")
    record2 = C.extract_claim(spec=_spec(), capture=again)
    assert record2.evidence.capture_hash != record.evidence.capture_hash
    _, created_second = C.persist_claim(engine, record2)
    assert created_second is False

    rows = C.load_expanded_claims(engine)
    assert len(rows) == 1
    row = rows[0]
    assert len(row["evidence"]) == 2  # both captures retained
    assert len(row["provenance"]) >= 6  # methodology + metric locators, not just a sentence
    assert row["methodology"]["measurement_mode"] == "vendor_estimate"
    assert row["dates"]["measured_window"] == "Jan 2026"


def test_expanded_claims_never_expose_the_private_snapshot_path():
    """Issue #26: the claims payload exposes availability + hash, never the path.

    Raw captures are private evidence; a server filesystem path leaks internal
    layout and is the first half of leaking capture contents.
    """

    capture = _synthetic_capture()
    spec = _spec()
    spec["source"]["snapshot_path"] = "/srv/private-snapshots/abc123.html"
    record = C.extract_claim(spec=spec, capture=capture)
    engine = C.create_ledger_engine("sqlite+pysqlite:///:memory:")
    C.init_ledger(engine)
    C.persist_claim(engine, record)

    rows = C.load_expanded_claims(engine)
    assert len(rows) == 1
    evidence = rows[0]["evidence"]
    assert evidence, "expected at least one evidence row"
    for entry in evidence:
        assert "snapshot_path" not in entry
        assert entry["snapshot_available"] is True
        assert entry["capture_hash"]
    assert "/srv/private-snapshots" not in json.dumps(rows)


def test_superseding_claim_requires_a_predecessor():
    spec = _spec(relationship="supersedes")
    with pytest.raises(ValidationError):
        C.extract_claim(spec=spec, capture=_synthetic_capture())


# --- real public captures (acceptance evidence) ----------------------------- #


@pytest.mark.parametrize("source_id", sorted(CAPTURE_FILES))
def test_real_capture_quotes_all_trace(source_id):
    path = CAPTURE_DIR / CAPTURE_FILES[source_id]
    if not path.exists():
        pytest.skip(f"capture {path} not present (run scripts/build_claim_proof.py)")
    raw = path.read_bytes()
    capture = C.Capture(raw=raw, text=C.extract_capture_text(raw.decode("utf-8", "replace")))
    spec = next(s for s in C.load_spec_bundle(SPECS) if s["source"]["source_id"] == source_id)
    record = C.extract_claim(spec=spec, capture=capture)
    assert not C.check_against_capture(record, capture)
    assert record.evidence.raw_sha256 and len(record.evidence.raw_sha256) == 64


def test_real_bundle_covers_the_three_required_proof_types():
    topics = {s["topic"] for s in C.load_spec_bundle(SPECS)}
    source_ids = {s["source"]["source_id"] for s in C.load_spec_bundle(SPECS)}
    assert {"audience_usage", "citations_sources", "referrals_conversion"} <= topics
    assert "similarweb-most-visited-websites" in source_ids
    assert "yandex-ai-search-pretrain-2026-09" in source_ids
    assert "naver-ai-tab-launch-2026-06" in source_ids
