from datetime import date

import pytest
from pydantic import ValidationError

from ai_discovery.reconciliation import StudyClaim, compare_claims


def claim(id="a", **changes):
    fields = dict(
        id=id,
        evidence_ids=(f"e-{id}",),
        surface="chatgpt",
        subject="reddit.com",
        statement="Synthetic unit fixture, not product proof",
        metric="citation_share",
        denominator="all_citations",
        geography="US",
        mode="consumer_web",
        sampling_frame="same-panel",
        period_start=date(2026, 8, 14),
        period_end=date(2026, 8, 17),
        value=0.5,
        unit="percent",
    )
    return StudyClaim(**{**fields, **changes})


def test_same_context_same_value_supports_without_unearned_confidence_boost():
    result = compare_claims(claim(), claim("b"))
    assert result.relationship == "supports"
    assert result.confidence_adjustment == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("metric", "mention_share"),
        ("denominator", "top_sources"),
        ("geography", "China"),
        ("mode", "api"),
        ("sampling_frame", "other-panel"),
        ("surface", "gemini"),
        ("subject", "wikipedia.org"),
        ("unit", "fraction"),
    ],
)
def test_different_contexts_are_not_direct_conflicts(field, value):
    result = compare_claims(claim(), claim("b", **{field: value, "value": 16.8}))
    assert result.state == "methodologically_incomparable"
    assert field in result.differences
    assert result.relationship == "contextualises"


@pytest.mark.parametrize(
    "field",
    ["geography", "denominator", "mode", "sampling_frame", "period_start", "period_end", "value"],
)
def test_unknown_is_not_a_match(field):
    result = compare_claims(claim(**{field: None}), claim("b", **{field: None}))
    assert result.state == "unresolved"
    assert field in result.unknown_dimensions


def test_later_period_qualifies_not_erases_and_argument_order_does_not_matter():
    older = claim()
    newer = claim("b", period_start=date(2026, 9, 1), period_end=date(2026, 9, 2), value=16.8)
    for first, second in [(older, newer), (newer, older)]:
        result = compare_claims(first, second)
        assert result.state == "temporal_update"
        assert result.relationship == "updates"
        assert result.claim_ids == ("b", "a")
        assert "Claim b" in result.interpretation
    assert older.value == 0.5


def test_overlapping_different_windows_do_not_create_false_conflict():
    result = compare_claims(claim(), claim("b", period_end=date(2026, 8, 20), value=16.8))
    assert result.state == "methodologically_incomparable"
    assert result.differences == ("time_window",)


def test_same_measurement_context_conflict_preserves_inputs_and_provenance():
    first, second = claim(), claim("b", value=16.8)
    before = first.model_dump(), second.model_dump()
    result = compare_claims(first, second)
    assert result.state == "material_conflict"
    assert result.evidence_ids == ("e-a", "e-b")
    assert result.confidence_adjustment < 0
    assert (first.model_dump(), second.model_dump()) == before


def test_provisional_is_not_durable_change():
    result = compare_claims(claim(provisional=True), claim("b", value=16.8))
    assert result.state == "possible_transient_change"


def test_canonical_reddit_methodology_shape_is_incomparable_not_death_or_recovery():
    # Values are illustrative unit inputs; live captured evidence is separate proof.
    first = claim(geography=None, mode=None, sampling_frame="Promptwatch", provisional=True)
    second = claim(
        "b",
        metric="mention_share",
        denominator="summed_top_source_citations",
        sampling_frame="Ahrefs Brand Radar",
        value=16.8,
        period_start=date(2026, 9, 1),
        period_end=None,
    )
    result = compare_claims(first, second)
    assert result.state == "methodologically_incomparable"
    assert result.confidence_adjustment < 0
    assert "denominator" in result.differences
    assert "provisional" in result.interpretation


def test_self_relation_invalid():
    with pytest.raises(ValueError):
        compare_claims(claim(), claim())


@pytest.mark.parametrize(
    "changes", [{"value": float("nan")}, {"value": float("inf")}, {"period_end": date(2025, 1, 1)}]
)
def test_bad_measurements_rejected(changes):
    with pytest.raises(ValidationError):
        claim(**changes)


@pytest.mark.parametrize("value", ["", " ", "unknown", "Unknown", "undocumented"])
def test_textual_unknown_does_not_make_comparison_known(value):
    assert compare_claims(claim(mode=value), claim("b", mode=value)).state == "unresolved"
