"""Parser-fidelity test: run the real extraction against the committed captures."""

import json
from pathlib import Path

import pytest

from ai_discovery.claims import Capture, extract_capture_text, extract_claim

PROOF = Path(__file__).resolve().parents[1] / "proof" / "claim_ledger"
CAPTURES = PROOF / "captures"
SPECS = PROOF / "claim_specs.json"


@pytest.fixture
def specs():
    return json.loads(SPECS.read_text())


def test_spec_file_exists(specs):
    assert specs["extraction_version"]
    assert len(specs["claims"]) >= 4


def test_captures_exist():
    html_files = list(CAPTURES.glob("*.html"))
    assert len(html_files) >= 3, f"expected ≥3 capture files, got {len(html_files)}"


@pytest.mark.parametrize(
    "capture_id",
    [
        "similarweb-most-visited-websites",
        "sistrix-ai-citation-drift",
        "yandex-ai-search-pretrain-2026-09",
        "naver-ai-tab-launch-2026-06",
    ],
)
def test_quote_locators_present_in_captured_text(capture_id, specs):
    """Every locator quote in claim_specs.json must appear verbatim in the captured text."""
    capture_file = CAPTURES / f"{capture_id}.html"
    if not capture_file.exists():
        pytest.skip(f"capture file {capture_id} not present")
    raw_html = capture_file.read_text(encoding="utf-8", errors="replace")
    capture = Capture(
        raw=raw_html.encode("utf-8"),
        text=extract_capture_text(raw_html),
    )
    matched_specs = [s for s in specs["claims"] if s["source"]["source_id"] == capture_id]
    if not matched_specs:
        pytest.skip(f"no claim spec for {capture_id}")
    for spec in matched_specs:
        methodology = spec.get("methodology") or {}
        for field_name in (
            "metric_family",
            "metric_definition",
            "denominator",
            "prompt_universe",
            "sample_size",
            "unit_of_analysis",
            "time_window",
        ):
            field = methodology.get(field_name)
            if not field:
                continue
            quote = field.get("quote")
            if not quote:
                continue
            assert quote in capture.text, (
                f"quote for {field_name} not found verbatim in {capture_id} capture: {quote[:60]}..."
            )


def test_extract_claim_produces_valid_record(specs):
    """The extraction pipeline produces a valid ClaimRecord from a real spec + capture."""
    spec = specs["claims"][0]
    capture_id = spec["source"]["source_id"]
    capture_file = CAPTURES / f"{capture_id}.html"
    if not capture_file.exists():
        pytest.skip(f"capture file {capture_id} not present")
    raw_html = capture_file.read_text(encoding="utf-8", errors="replace")
    capture = Capture(
        raw=raw_html.encode("utf-8"),
        text=extract_capture_text(raw_html),
    )
    record = extract_claim(spec=spec, capture=capture)
    assert record.claim_id
    assert record.claim_id == spec.get("claim_id", record.claim_id)
    assert record.topic == spec["topic"]
    assert record.statement == spec["statement"]
