"""Regression tests for the two systemic extraction-loss causes (issue #48).

Measured on the 2026-09-19 production proving run, the funnel was
51 configured sources → 12 captures → 12 with extracted text → **1** validated
claim. Two systemic, non-integrity causes accounted for most of the loss:

1. **All-or-nothing schema validation.** The provider returns claims as
   stringified JSON inside the tool-call payload (Gemini on OpenRouter does this
   for large documents). The primary Instructor parse then fails, and the
   JSON-mode fallback validated the *whole* array with one Pydantic call — so one
   malformed claim (e.g. a `optimisation_implication` topic the schema rejects, or
   a too-short statement) discarded an entire document's worth of good claims.
   Fix: validate claim-by-claim and keep the valid ones.

2. **Source-class vocabulary mismatch.** `config/sources.yaml` uses registry
   classes (`visibility_research`, `editorial_discovery`, `open_research`,
   `open_discovery`) that were absent from the ledger's `SourceClass` literal, so
   every otherwise-quote-verified claim from those 19 sources was rejected at
   record-construction time. Fix: the literal now covers the acquisition
   vocabulary.

These tests use no network: the fallback path is exercised directly with a
synthetic provider payload.
"""

from __future__ import annotations

import json

from ai_discovery.claim_models import CLAIM_TOPICS
from ai_discovery.confidence import SOURCE_AUTHORITY
from ai_discovery.semantic import (
    ExtractedClaim,
    _load_claims_payload,
    _validate_claims_individually,
)


def real_config_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "config" / "sources.yaml"


def tmp_path_file():
    import tempfile
    from pathlib import Path

    return Path(tempfile.mkdtemp()) / "sources.yaml"


def _configured_source_classes() -> set[str]:
    """Every source class actually used by config/sources.yaml.

    Derived from the real config (no network) so a class added to the registry
    without a ledger counterpart fails here — the exact drift this guards.
    """

    from ai_discovery.registry import load_sources_config

    return {s.source_class for s in load_sources_config().sources}


def _good_claim() -> dict:
    return {
        "topic": "citations_sources",
        "statement": "Reddit is the most-cited domain in ChatGPT answers.",
        "surfaces": ["chatgpt"],
        "capture_anchor": "Reddit is the most-cited domain in ChatGPT answers.",
        "metrics": [
            {
                "label": "citation share",
                "value": 16.8,
                "value_quote": "16.8% of all citations",
            }
        ],
    }


def test_registry_source_classes_are_valid_ledger_classes():
    """Every class config/sources.yaml actually uses is a valid ledger class."""

    from typing import get_args

    from ai_discovery.claim_models import SourceClass

    literal = set(get_args(SourceClass))
    missing = sorted(_configured_source_classes() - literal)
    assert not missing, f"registry source classes absent from SourceClass literal: {missing}"


def test_registry_source_classes_have_confidence_authority():
    """No class config/sources.yaml actually uses falls through to the default."""

    for cls in _configured_source_classes():
        assert cls in SOURCE_AUTHORITY, f"{cls} missing from SOURCE_AUTHORITY"


def test_loader_rejects_unknown_source_class():
    """A registry class with no ledger counterpart fails loudly at load time."""

    import yaml

    from ai_discovery.registry import load_sources_config

    raw = yaml.safe_load(real_config_path().read_text())
    raw["sources"][0]["class"] = "totally_unmapped_class"
    tmp = tmp_path_file()
    tmp.write_text(yaml.safe_dump(raw))
    try:
        load_sources_config(tmp)
    except ValueError as error:
        assert "totally_unmapped_class" in str(error)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("loader accepted an unmapped source class")


def test_stringified_json_claim_objects_are_normalised():
    """Providers may return each claim as a JSON string; parse them."""

    payload = json.dumps({"claims": [json.dumps(_good_claim()), _good_claim()]})
    loaded = _load_claims_payload(payload)
    assert len(loaded["claims"]) == 2
    assert all(isinstance(c, dict) for c in loaded["claims"])


def test_bare_array_payload_is_wrapped():
    loaded = _load_claims_payload(json.dumps([_good_claim(), _good_claim()]))
    assert len(loaded["claims"]) == 2


def test_unparseable_string_claim_is_skipped_not_fatal():
    payload = json.dumps({"claims": ["{not json", _good_claim()]})
    loaded = _load_claims_payload(payload)
    assert len(loaded["claims"]) == 1


def test_malformed_aggregate_claims_string_does_not_raise():
    """A malformed stringified `claims` value degrades, never raises (F1)."""

    loaded = _load_claims_payload('{"claims": "[not json"}')
    assert loaded == {"claims": []}


def test_malformed_top_level_payload_does_not_raise():
    assert _load_claims_payload("{not json at all") == {"claims": []}


def test_null_valued_metric_claims_are_not_admitted():
    """A claim whose only metric value is null stays unknown, not claimable (F2)."""

    from ai_discovery.semantic import _has_valued_metric

    assert not _has_valued_metric({"metrics": [{"label": "x", "value": None}]})
    assert not _has_valued_metric({"metrics": []})
    assert _has_valued_metric({"metrics": [{"label": "x", "value": 0}]})


def test_one_malformed_claim_does_not_discard_valid_siblings():
    """The core regression: a bad claim must not veto the good ones."""

    bad = dict(_good_claim(), topic="not_a_real_topic")
    second_bad = dict(_good_claim(), statement="x")  # below min_length
    good = _good_claim()
    valid, rejected = _validate_claims_individually([bad, second_bad, good])
    assert len(valid) == 1
    assert valid[0]["topic"] == good["topic"]
    assert len(rejected) == 2


def test_individually_validated_claims_re_validate():
    """Whatever survives per-claim validation is a real ExtractedClaim."""

    valid, rejected = _validate_claims_individually([_good_claim()])
    assert not rejected
    models = [ExtractedClaim.model_validate(c) for c in valid]
    assert models[0].topic in CLAIM_TOPICS
