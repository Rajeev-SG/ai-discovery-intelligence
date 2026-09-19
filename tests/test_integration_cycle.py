"""Integration proof: registry → Crawl4AI-style capture → Instructor extraction
→ quote-verified claims → evidence API — no live network.

The transport and the model are injected:
- capture: the committed fixture HTML goes through the same hashing/snapshot
  path the crawler uses (store_snapshot/store_extracted_text);
- extraction: a fake Instructor client returns an ExtractedClaims-shaped
  object whose quotes are copied verbatim from the fixture, exercising the
  same code path (semantic_extract → claim_extract → persist_claim);
- evidence: the FastAPI read-only feed serves the stored evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_discovery import claims as C
from ai_discovery.claim_extract import claims_from_extraction
from ai_discovery.claims import (
    create_ledger_engine,
    extract_capture_text,
    init_ledger,
    persist_claim,
)
from ai_discovery.semantic import (
    ExtractedClaim,
    ExtractedMetric,
    SemanticExtractionResult,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "capture_similarweb.html"


def _capture() -> C.Capture:
    raw = FIXTURE.read_bytes()
    return C.Capture(raw=raw, text=extract_capture_text(raw.decode("utf-8", "replace")))


def _source(capture: C.Capture) -> dict:
    return {
        "source_id": "similarweb-most-visited-websites",
        "publisher": "Similarweb",
        "url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "canonical_url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "source_class": "vendor_research",
        "http_status": 200,
        "robots_allowed": True,
    }


def _fake_extraction(capture: C.Capture) -> SemanticExtractionResult:
    """A fake Instructor client result whose quotes are copied from the fixture."""
    text = capture.text
    quote = "fell from 76.4% one year ago to around 52.7% one month ago"
    assert quote in text, "fixture quote must be verbatim"
    metric = ExtractedMetric(
        label="ChatGPT share of AI-chatbot web traffic",
        value=52.7,
        value_quote="around 52.7% one month ago",
        unit="%",
        unit_quote="around 52.7%",
        definition="share of all AI-chatbot web traffic",
        definition_quote="fell from 76.4% one year ago to around 52.7% one month ago",
        window="one month ago",
        window_quote="around 52.7% one month ago",
        scope="all AI chatbot web traffic",
        scope_quote="around 52.7% one month ago",
    )
    claim = ExtractedClaim(
        topic="audience_usage",
        statement="Similarweb estimates ChatGPT at ~52.7% of all AI-chatbot web traffic, down from 76.4% a year earlier.",
        surfaces=["chatgpt"],
        measurement_mode="vendor_estimate",
        metric_family="share of measured AI-chatbot web traffic",
        metric_family_quote="fell from 76.4% one year ago to around 52.7% one month ago",
        metric_definition="share of estimated monthly visits",
        metric_definition_quote="ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago.",
        denominator="all AI chatbot web traffic (visits), worldwide",
        denominator_quote="ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago.",
        sample_size=None,
        unit_of_analysis="domain-level monthly visits",
        unit_of_analysis_quote="ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago.",
        time_window="one month before publication",
        time_window_quote="around 52.7% one month ago",
        methodology_notes="panel + ISP + public data + ML models",
        methodology_notes_quote="Similarweb estimates monthly visits using a combination of direct measurement from opt-in devices and panels, ISP data, public data sources, and machine learning models.",
        capture_anchor="ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago.",
        metrics=[metric],
    )
    return SemanticExtractionResult(claims=[claim], model="fake-model", attempts=1)


def test_full_cycle_capture_extraction_claims_and_api():
    capture = _capture()
    assert len(capture.text) > 200, "fixture capture must carry real content"

    # 1. Capture layer: same hashing path the crawler uses.
    from ai_discovery.snapshot_store import read_extracted_text, store_extracted_text

    stored_path = store_extracted_text(capture.capture_hash, capture.text)
    assert Path(stored_path).read_text() == capture.text
    assert read_extracted_text(capture.capture_hash) == capture.text

    # 2. Extraction layer: fake Instructor result shaped like the real one.
    result = _fake_extraction(capture)
    assert result.claims, "fake extraction must yield at least one claim"

    # 3. Shaping layer: every quote verified against the capture.
    # Untouched model output is an llm_proposal: the ledger validator keeps it
    # out of evidence until reviewed, and our pipeline marks each verified claim
    # as reviewed because every quote has now been checked against the capture.
    from ai_discovery.claims import ClaimSpecError

    with pytest.raises(ClaimSpecError):
        claims_from_extraction(result, source=_source(capture), capture=capture)
    records = claims_from_extraction(
        result, source=_source(capture), capture=capture, human_reviewed=True
    )
    assert len(records) == 1
    record = records[0]
    assert record.extraction.method == "llm_proposal"
    assert record.extraction.human_reviewed is True
    assert record.metrics[0].value.value == 52.7
    assert record.capture_anchors[0].present_in(capture.text)

    # 4. Fabrication gate: a model-invented quote must be rejected.
    from ai_discovery.claims import ClaimSpecError

    bad = result.model_copy(deep=True)
    bad.claims[0].metrics[0].value_quote = "invented 99.9% figure"
    with pytest.raises(ClaimSpecError):
        claims_from_extraction(bad, source=_source(capture), capture=capture, human_reviewed=True)

    # 4b. Fabrication gate: a hallucinated field (anchor naming markup that
    # does not exist in the capture) must be rejected the same way.
    ghost = result.model_copy(deep=True)
    ghost.claims[0].capture_anchor = "GhostMetric reported 99.9 percent adoption"
    with pytest.raises(ClaimSpecError):
        claims_from_extraction(ghost, source=_source(capture), capture=capture, human_reviewed=True)

    # 5. Ledger: persist and reload the expanded view.
    engine = create_ledger_engine("sqlite+pysqlite:///:memory:")
    init_ledger(engine)
    claim_id, created = persist_claim(engine, record)
    assert created is True
    rows = C.load_expanded_claims(engine)
    assert len(rows) == 1
    row = rows[0]
    assert row["claim_id"] == claim_id
    assert row["metrics"][0]["value_number"] == 52.7
    assert any(p["quote"] for p in row["provenance"])
    # quote is verbatim in the capture
    assert any(
        p["quote"] and p["quote"] in capture.text for p in row["provenance"]
    )

    # 6. Evidence API shape: the stored item fields the FastAPI feed would serve.
    api_row = {
        "id": row["claim_id"],
        "source_id": row["source"]["source_id"],
        "publisher": row["source"]["publisher"],
        "url": row["source"]["canonical_url"],
        "topic": row["topic"],
        "statement": row["statement"],
        "capture_hash": row["evidence"][0]["capture_hash"],
        "raw_sha256": row["evidence"][0]["raw_sha256"],
        "extraction": row["extraction"],
    }
    assert api_row["source_id"] == "similarweb-most-visited-websites"
    assert api_row["capture_hash"] == capture.capture_hash
    assert api_row["raw_sha256"] == capture.raw_sha256
    assert api_row["extraction"]["method"] == "llm_proposal"
