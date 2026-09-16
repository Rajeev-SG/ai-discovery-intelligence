import datetime as dt

from ai_discovery.coverage import CoverageGap, CoverageMatrix, GapCategory, Priority


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
