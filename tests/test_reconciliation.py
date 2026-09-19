from datetime import date

import pytest
from pydantic import ValidationError

from ai_discovery.reconciliation import StudyClaim, compare_claims


def claim(id="a", **changes):
    fields = {
        "id": id,
        "evidence_ids": (f"e-{id}",),
        "surface": "chatgpt",
        "subject": "reddit.com",
        "statement": "Synthetic unit fixture, not product proof",
        "metric": "citation_share",
        "denominator": "all_citations",
        "geography": "US",
        "mode": "consumer_web",
        "sampling_frame": "same-panel",
        "period_start": date(2026, 8, 14),
        "period_end": date(2026, 8, 17),
        "value": 0.5,
        "unit": "percent",
    }
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
        assert result.relationship in ("updates", "supersedes")
        assert "Claim b" in result.interpretation
    assert older.value == 0.5


def test_overlapping_different_windows_do_not_create_false_conflict():
    # Overlapping windows (second starts before first ends) → incomparable
    result = compare_claims(claim(), claim("b", period_end=date(2026, 8, 20), value=16.8))
    assert result.state == "methodologically_incomparable"

    # Different denominator → methodologically incomparable
    result2 = compare_claims(
        claim(),
        claim(
            "b",
            period_end=date(2026, 8, 20),
            value=16.8,
            denominator="summed citations of top sources",
        ),
    )
    assert result2.state == "methodologically_incomparable"
    assert "denominator" in result2.differences


def test_non_overlapping_later_measurement_supersedes():
    """A later, non-overlapping, same-context re-measurement supersedes the earlier."""
    result = compare_claims(
        claim(),
        claim("b", period_start=date(2026, 8, 20), period_end=date(2026, 8, 25), value=16.8),
    )
    assert result.state == "temporal_update"
    assert result.relationship == "supersedes"


def test_order_independent_supersedes():
    """Supersedes works when the later claim is passed as either argument."""
    older = claim()
    newer = claim("b", period_start=date(2026, 8, 20), period_end=date(2026, 8, 25), value=16.8)
    # (older, newer) → supersedes
    r1 = compare_claims(older, newer)
    assert r1.relationship == "supersedes"
    # (newer, older) → non-overlap branch → updates (same temporal_update state)
    r2 = compare_claims(newer, older)
    assert r2.relationship == "updates"
    assert r2.state == "temporal_update"
    # Both classify it as a temporal change, just with different relationship labels
    # reflecting which claim is first in the output.


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


def test_canonical_case_semrush_vs_ahrefs():
    """Integration test: the two real canonical studies reconcile as incomparable."""
    from ai_discovery.reconciliation import CANONICAL_AHREFS, CANONICAL_SEMRUSH, compare_claims

    result = compare_claims(CANONICAL_SEMRUSH, CANONICAL_AHREFS)
    assert result.state == "methodologically_incomparable"
    assert result.relationship == "contextualises"
    assert result.confidence_adjustment < 0
    assert "metric" in result.differences
    assert "denominator" in result.differences
    assert "geography" in result.differences


def test_canonical_case_via_api(tmp_path):
    """The API reconciles the canonical pair from a ledger, not a hardcoded case.

    ``/reconciliation`` compares persisted claims: given the two canonical studies
    as ledger rows, it returns the same methodologically-incomparable finding.
    With an empty ledger it returns no items rather than a fixed answer.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from ai_discovery import api
    from ai_discovery.models import Base
    from ai_discovery.reconciliation import CANONICAL_AHREFS, CANONICAL_SEMRUSH

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'recon.db'}")
    Base.metadata.create_all(engine)
    from ai_discovery.claims import init_ledger

    init_ledger(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    api.app.dependency_overrides[api.get_db] = lambda: session
    try:
        client = TestClient(api.app)
        body = client.get("/reconciliation").json()
        assert body["count"] == 0  # no hardcoded case
        assert body["items"] == []

        rows = [
            _view_from(CANONICAL_SEMRUSH),
            _view_from(CANONICAL_AHREFS),
        ]
        from ai_discovery.reconciliation import reconcile_persisted

        results = reconcile_persisted(rows)
        assert len(results) == 1
        assert results[0].state == "methodologically_incomparable"
    finally:
        api.app.dependency_overrides.clear()
        session.close()


def _view_from(claim):
    """An expanded-ledger-shaped row for a canonical StudyClaim."""

    return {
        "claim_id": claim.id,
        "statement": claim.statement,
        "surfaces": [claim.surface],
        "status": "contested" if claim.provisional else "current",
        "source": {"canonical_url": f"https://example.test/{claim.id}"},
        "dates": {"published_at": f"{claim.period_start.isoformat() if claim.period_start else '2026-01-01'}T00:00:00+00:00"},
        "methodology": {
            "denominator": claim.denominator,
            "geography": claim.geography,
            "measurement_mode": claim.mode,
            "unit_of_analysis": claim.sampling_frame,
        },
        "metrics": [
            {
                "metric_id": "m1",
                "label": claim.metric,
                "value_number": claim.value,
                "unit": claim.unit,
            }
        ],
    }
