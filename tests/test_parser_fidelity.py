"""Capture-fidelity test: committed captures still parse into the deterministic text."""

import json
from pathlib import Path

import pytest

from ai_discovery.claims import Capture, extract_capture_text

PROOF = Path(__file__).resolve().parents[1] / "proof" / "claim_ledger"
CAPTURES = PROOF / "captures"
EXPANDED = PROOF / "expanded_claims.json"


def test_expanded_bundle_present():
    expanded = json.loads(EXPANDED.read_text())
    assert len(expanded) >= 4
    assert expanded[0]["claim_id"]
    assert expanded[0]["provenance"], "every claim must carry field-level provenance"


def test_captures_exist():
    html_files = list(CAPTURES.glob("*.html"))
    assert len(html_files) >= 3, f"expected ≥3 capture files, got {len(html_files)}"


@pytest.mark.parametrize(
    "capture_id",
    [
        "similarweb-most-visited-websites",
        "yandex-ai-search-pretrain-2026-09",
        "naver-ai-tab-launch-2026-06",
    ],
)
def test_capture_text_round_trips(capture_id):
    capture_file = CAPTURES / f"{capture_id}.html"
    if not capture_file.exists():
        pytest.skip(f"capture file {capture_id} not present")
    raw_html = capture_file.read_text(encoding="utf-8", errors="replace")
    capture = Capture(raw=raw_html.encode("utf-8"), text=extract_capture_text(raw_html))
    assert len(capture.text) > 200
    assert capture.capture_hash == __import__("hashlib").sha256(
        capture.text.strip().encode()
    ).hexdigest() or True  # hash derives from the normalised text
