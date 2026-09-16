import datetime as dt

from ai_discovery.coverage import (
    CoverageGap,
    CoverageMatrix,
    GapCategory,
    LedgerDerivedMatrix,
    Priority,
)


def gap(**kw):
    defaults: dict = {
        "id": "g1",
        "surfaces": ["chatgpt"],
        "topics": ["retrieval"],
        "geographies": ["global"],
        "category": GapCategory.under_documented,
        "description": "test",
        "priority": Priority.medium,
        "importance_score": 0.6,
    }
    return CoverageGap(**{**defaults, **kw})


def test_matrix_for_surface():
    m = CoverageMatrix([gap(id="a", surfaces=["chatgpt"]), gap(id="b", surfaces=["gemini"])])
    assert [g.id for g in m.for_surface("chatgpt")] == ["a"]


def test_matrix_by_priority():
    m = CoverageMatrix([gap(id="a", priority=Priority.high), gap(id="b", priority=Priority.low)])
    assert [g.id for g in m.by_priority(Priority.high)] == ["a"]


def test_matrix_by_category():
    m = CoverageMatrix(
        [
            gap(id="a", category=GapCategory.no_evidence),
            gap(id="b", category=GapCategory.stale_evidence),
        ]
    )
    assert [g.id for g in m.by_category(GapCategory.no_evidence)] == ["a"]


def test_research_queue_high_first():
    m = CoverageMatrix(
        [
            gap(id="low", priority=Priority.low, importance_score=0.9),
            gap(id="high", priority=Priority.high, importance_score=0.5),
            gap(id="med", priority=Priority.medium, importance_score=0.7),
        ]
    )
    assert [g.id for g in m.research_queue()] == ["high", "med", "low"]


def test_research_queue_importance_within_priority():
    m = CoverageMatrix(
        [
            gap(id="a", priority=Priority.high, importance_score=0.5),
            gap(id="b", priority=Priority.high, importance_score=0.9),
        ]
    )
    assert [g.id for g in m.research_queue()] == ["b", "a"]


def test_stale_after_days():
    g = gap(last_verified=dt.datetime(2026, 6, 1, tzinfo=dt.UTC), stale_after_days=30)
    m = CoverageMatrix([g])
    assert m.is_stale(g, now=dt.datetime(2026, 9, 16, tzinfo=dt.UTC))
    assert not m.is_stale(g, now=dt.datetime(2026, 6, 15, tzinfo=dt.UTC))


def test_not_stale_without_last_verified():
    g = gap(stale_after_days=30)
    m = CoverageMatrix([g])
    assert not m.is_stale(g)


def test_not_stale_without_days():
    g = gap(last_verified=dt.datetime(2026, 6, 1, tzinfo=dt.UTC))
    m = CoverageMatrix([g])
    assert not m.is_stale(g)


def test_fetch_failed_is_distinct_from_no_evidence():
    """A fetch failure must never be categorised as no_evidence."""
    m = CoverageMatrix(
        [
            gap(id="fetch-fail", category=GapCategory.fetch_failed),
            gap(id="no-ev", category=GapCategory.no_evidence),
        ]
    )
    assert [g.id for g in m.by_category(GapCategory.fetch_failed)] == ["fetch-fail"]
    assert [g.id for g in m.by_category(GapCategory.no_evidence)] == ["no-ev"]
    assert GapCategory.fetch_failed != GapCategory.no_evidence


def test_derived_matrix_from_claim_ledger():
    """Given a ledger with a fresh claim and an expired claim for one surface and nothing for another, the matrix reports covered / stale / no_evidence."""
    import types

    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    fresh_claim = types.SimpleNamespace(
        surfaces=["chatgpt"],
        topics=["citation"],
        geographies=["global"],
        observed_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC),
        url="https://example.com/fresh",
    )
    stale_claim = types.SimpleNamespace(
        surfaces=["gemini"],
        topics=["citation"],
        geographies=["global"],
        observed_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        url="https://example.com/stale",
    )
    dm = LedgerDerivedMatrix([fresh_claim, stale_claim], stale_after_days=90, now=now)
    gaps = dm.derive()
    by_surface = {}
    for g in gaps:
        by_surface[g.surfaces[0]] = g.category
    assert by_surface.get("chatgpt") == GapCategory.single_source, (
        f"fresh single source should be single_source, got {by_surface.get('chatgpt')}"
    )
    assert by_surface.get("gemini") == GapCategory.stale_evidence, (
        f"expired claim should be stale_evidence, got {by_surface.get('gemini')}"
    )


def test_derived_matrix_empty_for_missing_surface():
    """A surface with no claims should produce no gap entry (not covered, not stale)."""
    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    dm = LedgerDerivedMatrix([], stale_after_days=90, now=now)
    gaps = dm.derive()
    assert gaps == []


def test_registry_surfaces_produce_no_evidence():
    """A surface in the registry with zero claims must produce a no_evidence gap."""

    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    dm = LedgerDerivedMatrix([], surfaces_registry=["doubao", "qwen"], stale_after_days=90, now=now)
    gaps = dm.derive()
    categories = {g.surfaces[0]: g.category for g in gaps}
    assert categories.get("doubao") == GapCategory.no_evidence
    assert categories.get("qwen") == GapCategory.no_evidence


def test_computed_priority_from_importance():
    """Priority should be computed from importance_score, not hardcoded medium."""
    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    dm = LedgerDerivedMatrix(
        [],
        surfaces_registry=["a", "b", "c"],
        stale_after_days=90,
        now=now,
        importance_overrides={"a": 0.9, "b": 0.6, "c": 0.3},
    )
    gaps = dm.derive()
    by_surface = {g.surfaces[0]: g for g in gaps}
    assert by_surface["a"].priority == Priority.high
    assert by_surface["b"].priority == Priority.medium
    assert by_surface["c"].priority == Priority.low


def test_stale_urls_retained_in_single_source():
    """One fresh + two stale claims → single_source with stale URLs in metadata."""
    import types

    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    fresh = types.SimpleNamespace(
        surfaces=["chatgpt"],
        topics=["citation"],
        geographies=["global"],
        observed_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC),
        url="https://fresh.example",
    )
    stale_a = types.SimpleNamespace(
        surfaces=["chatgpt"],
        topics=["citation"],
        geographies=["global"],
        observed_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
        url="https://stale-a.example",
    )
    stale_b = types.SimpleNamespace(
        surfaces=["chatgpt"],
        topics=["citation"],
        geographies=["global"],
        observed_at=dt.datetime(2026, 2, 1, tzinfo=dt.UTC),
        url="https://stale-b.example",
    )
    dm = LedgerDerivedMatrix([fresh, stale_a, stale_b], stale_after_days=90, now=now)
    gaps = dm.derive()
    assert gaps[0].category == GapCategory.single_source
    assert "https://stale-a.example" in gaps[0].metadata["stale_evidence_urls"]
    assert "https://stale-b.example" in gaps[0].metadata["stale_evidence_urls"]


def test_published_at_only_not_fresh():
    """A claim with only published_at (no observed_at) should be treated as not fresh."""
    import types

    now = dt.datetime(2026, 9, 16, tzinfo=dt.UTC)
    published_only = types.SimpleNamespace(
        surfaces=["x"],
        topics=["t"],
        geographies=["g"],
        observed_at=None,
        published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC),
        url="https://x",
    )
    dm = LedgerDerivedMatrix([published_only], stale_after_days=90, now=now)
    gaps = dm.derive()
    assert gaps[0].category == GapCategory.stale_evidence
