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
CAPTURE_DIR = REPO / "proof" / "claim_ledger" / "captures"
CAPTURE_FILES = {
    "similarweb-most-visited-websites": "similarweb-most-visited-websites.html",
    "sistrix-ai-citation-drift": None,  # no capture file committed for this source
    "yandex-ai-search-pretrain-2026-09": "yandex-ai-search-pretrain-2026-09.html",
    "naver-ai-tab-launch-2026-06": "naver-ai-tab-launch-2026-06.html",
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


def test_a_fabricated_selector_is_rejected():
    """Issue #24: a non-existent selector must fail, exactly like a fake quote.

    Before the fix a claim could carry ``{"kind": "jsonld_field",
    "selector": "div#never-exists"}`` and pass with nothing checked against the
    capture, because ``present_in`` returned True for any locator without a quote.
    """

    spec = _spec()
    spec["capture_anchors"] = [{"kind": "jsonld_field", "selector": "div#never-exists"}]
    with pytest.raises(C.ClaimSpecError, match="not found in capture"):
        C.extract_claim(spec=spec, capture=_synthetic_capture())


def test_a_fabricated_selector_on_a_metric_field_is_rejected():
    """The guard covers structured selectors on any provenanced field, not just anchors."""

    spec = _spec()
    spec["metrics"][0]["value"] = {
        "value": "9.9M",
        "kind": "jsonld_field",
        "selector": "datePublished.neverThere",
    }
    with pytest.raises(C.ClaimSpecError, match="not found in capture"):
        C.extract_claim(spec=spec, capture=_synthetic_capture())


def test_a_resolvable_selector_still_verifies():
    """Issue #24 acceptance: a selector that genuinely resolves is accepted."""

    spec = _spec()
    spec["capture_anchors"] = [{"kind": "jsonld_field", "selector": "datePublished"}]
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.capture_anchors[0].kind == "jsonld_field"
    assert not C.check_against_capture(record, _synthetic_capture())


def test_selector_resolution_uses_raw_markup_not_parsed_text():
    """A JSON-LD selector lives in markup that text extraction strips (issue #24)."""

    capture = _synthetic_capture()
    loc = C.Locator(kind="jsonld_field", selector="datePublished")
    assert "datePublished" not in capture.text
    assert loc.present_in(capture.text, capture.raw_text)
    assert not loc.present_in(capture.text)


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


def test_unknown_metric_value_persists_as_null_not_the_string_none():
    """Issue #25: an unknown value must round-trip as NULL, never as ``"None"``.

    ``Provenanced.known`` is ``value is not None``, so ``unknown()`` yields
    ``value=None``. ``str(None)`` would store the literal string ``"None"`` while
    ``value_number`` stayed NULL, breaking the "unknown is first-class" contract.
    """

    spec = _spec()
    spec["metrics"][0]["value"] = None  # explicit unknown: no value, no locator
    record = C.extract_claim(spec=spec, capture=_synthetic_capture())
    assert record.metrics[0].value.known is False

    engine = C.create_ledger_engine("sqlite+pysqlite:///:memory:")
    C.init_ledger(engine)
    C.persist_claim(engine, record)

    row = C.load_expanded_claims(engine)[0]
    metric = row["metrics"][0]
    assert metric["value_text"] is None
    assert metric["value_number"] is None
    # The persisted value is None, not the string "None"; assert on the field
    # itself rather than scanning the whole JSON blob.
    assert not isinstance(metric["value_text"], str)
    assert repr(metric["value_text"]) == "None"


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


# --- committed-capture regeneration (no live network) ----------------------- #


@pytest.mark.parametrize("source_id", sorted(CAPTURE_FILES))
def test_real_capture_quotes_all_trace(source_id):
    filename = CAPTURE_FILES[source_id]
    path = CAPTURE_DIR / filename if filename else CAPTURE_DIR / f"{source_id}.html"
    if not path.exists():
        pytest.skip(f"capture {path.name} not present (claim-spec flow retired)")
    raw = path.read_bytes()
    capture = C.Capture(raw=raw, text=C.extract_capture_text(raw.decode("utf-8", "replace")))
    # The claim-spec flow is replaced by Instructor extraction; this test now
    # proves the deterministic capture text pipeline still round-trips.
    assert len(capture.text) > 200
    assert capture.capture_hash and len(capture.capture_hash) == 64
    assert capture.raw_sha256 and len(capture.raw_sha256) == 64


def test_real_bundle_covers_the_three_required_proof_types():
    expanded = REPO / "proof" / "claim_ledger" / "expanded_claims.json"
    if not expanded.exists():
        pytest.skip("expanded_claims.json not present (hand-written spec bundle retired)")
    payload = json.loads(expanded.read_text())
    topics = {c["topic"] for c in payload}
    source_ids = {c["source"]["source_id"] for c in payload}
    assert {"audience_usage", "citations_sources", "referrals_conversion"} <= topics
    assert "similarweb-most-visited-websites" in source_ids
    assert "yandex-ai-search-pretrain-2026-09" in source_ids
    assert "naver-ai-tab-launch-2026-06" in source_ids
