"""Issue #57 corpus rebalance: mechanics claim specs extract from real captures.

These tests run the real extraction lane against the *committed real captures*,
so the mechanics corpus growth is proven to be source-backed: every quoted value
must be present verbatim in the capture, or extraction refuses the claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_discovery.claims import Capture, extract_capture_text, extract_claim

REPO = Path(__file__).resolve().parents[1]
CAPTURES = REPO / "proof" / "claim_ledger" / "captures"
SPECS = REPO / "proof" / "claim_ledger" / "mechanics_claim_specs.json"

REQUIRED_TOPICS = {"retrieval_index", "crawler_index_policy", "citations_sources"}
REQUIRED_SURFACES = {"chatgpt", "google-ai-mode", "google-ai-overviews", "perplexity"}


@pytest.fixture(scope="module")
def bundle() -> dict:
    return json.loads(SPECS.read_text())


@pytest.fixture(scope="module")
def captures() -> dict[str, Capture]:
    out: dict[str, Capture] = {}
    for path in CAPTURES.glob("*.html"):
        raw = path.read_bytes()
        out[path.stem] = Capture(
            raw=raw, text=extract_capture_text(raw.decode("utf-8", errors="replace"))
        )
    return out


def _records(bundle, captures):
    records = []
    for spec in bundle["claims"]:
        src = spec["source"]["source_id"]
        if src not in captures:
            continue
        records.append(extract_claim(spec=spec, capture=captures[src]))
    return records


def test_specs_cover_the_priority_mechanics_topics(bundle):
    topics = {c["topic"] for c in bundle["claims"]}
    assert REQUIRED_TOPICS <= topics


def test_specs_cover_the_core_surfaces(bundle):
    surfaces = {s for c in bundle["claims"] for s in c["surfaces"]}
    assert REQUIRED_SURFACES <= surfaces


def test_every_spec_extracts_against_its_real_capture(bundle, captures):
    # Extract_claim re-verifies every declared quote against the capture bytes; a
    # fabricated value cannot survive. One record per spec.
    records = _records(bundle, captures)
    assert len(records) == len(bundle["claims"])


def test_no_new_audience_or_market_share_claims_added(bundle):
    # Corpus growth must be mechanics, not more market-share noise (issue #57).
    topics = {c["topic"] for c in bundle["claims"]}
    assert "audience_usage" not in topics
    assert "referrals_conversion" not in topics


def test_growth_is_all_mechanics_topics(bundle):
    from ai_discovery.mechanics import NON_MECHANICS_TOPICS

    for claim in bundle["claims"]:
        assert claim["topic"] not in NON_MECHANICS_TOPICS, claim["topic"]


def test_mechanics_lane_is_wired_into_the_pipeline():
    # The mechanics extraction is operator-facing, not a one-off script: it is a
    # Dagster asset with a real callable, so the scheduled pipeline can run it.
    from ai_discovery.pipeline import defs

    names = {a.key.to_user_string() for a in defs.assets}
    assert "mechanics_claims" in names
    # A registered asset with real node definitions is runnable by the scheduler.
    asset = next(a for a in defs.assets if a.key.to_user_string() == "mechanics_claims")
    assert asset.node_def is not None


def test_build_records_is_the_shared_extraction_path():
    # One code path for the CLI and the pipeline asset.
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "builder", repo / "scripts" / "build_mechanics_claims.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    records = mod.build_records()
    assert len(records) == len(mod.specs())
    assert all(r.extraction.method == "deterministic_parser" for r in records)


def test_mechanics_claims_span_multiple_core_surfaces():
    # The rebalance must reach beyond a single surface (review finding 1).
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "builder", repo / "scripts" / "build_mechanics_claims.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    surfaces = {s for c in mod.specs() for s in c["surfaces"]}
    # At least five distinct core surfaces gain mechanics evidence.
    core = {
        "chatgpt", "google-ai-mode", "google-ai-overviews", "perplexity",
        "naver-ai", "yandex-ai-search",
    }
    assert len(surfaces & core) >= 5
