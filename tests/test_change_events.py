import datetime as dt

import pytest

from ai_discovery.change_events import ChangeEvent, EventStore, EventType


def ev(**kw):
    defaults = {
        event_type=EventType.citation_source_shift,
        title="Synthetic unit fixture, not product proof",
        description="fixture",
        surfaces=["chatgpt"],
        claims=["c1"],
        evidence_urls=["https://example.com/s"],
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
        published_at=dt.datetime(2026, 8, 26, tzinfo=dt.UTC),
        
    )
    return ChangeEvent(**{**defaults, **kw})


def test_append_and_get():
    store = EventStore()
    e = ev(id="abc")
    store.append(e)
    assert store.get("abc") is e
    assert len(store.all()) == 1


def test_no_overwrite():
    store = EventStore()
    store.append(ev(id="abc"))
    with pytest.raises(ValueError):
        store.append(ev(id="abc"))


def test_by_surface():
    store = EventStore()
    store.append(ev(id="a", surfaces=["chatgpt"]))
    store.append(ev(id="b", surfaces=["gemini"]))
    assert [e.id for e in store.by_surface("chatgpt")] == ["a"]
    assert [e.id for e in store.by_surface("gemini")] == ["b"]


def test_by_type():
    store = EventStore()
    store.append(ev(id="a", event_type=EventType.product_launch))
    store.append(ev(id="b", event_type=EventType.audience_shift))
    assert [e.id for e in store.by_type(EventType.product_launch)] == ["a"]


def test_dedupe_removes_repeats():
    store = EventStore()
    store.append(ev(id="a", dedupe_key="x"))
    store.append(ev(id="b", dedupe_key="x"))
    store.append(ev(id="c", dedupe_key="y"))
    result = store.dedupe()
    assert [e.id for e in result] == ["a", "c"]


def test_timeline_global():
    store = EventStore()
    store.append(ev(id="a", published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC), dedupe_key="sep"))
    store.append(ev(id="b", published_at=dt.datetime(2026, 8, 26, tzinfo=dt.UTC), dedupe_key="aug"))
    assert [e.id for e in store.timeline()] == ["b", "a"]


def test_timeline_per_surface():
    store = EventStore()
    store.append(ev(id="a", surfaces=["chatgpt"], dedupe_key=None))
    store.append(ev(id="b", surfaces=["gemini"], dedupe_key=None))
    assert [e.id for e in store.timeline("chatgpt")] == ["a"]


def test_event_is_frozen():
    e = ev(id="x")
    with pytest.raises(ValidationError, TypeError, ValueError, AttributeError):
        e.title = "mutated"


def test_supersedes_field():
    e = ev(id="y", supersedes="x")
    assert e.supersedes == "x"


def test_type_values():
    assert EventType.product_launch.value == "product_launch"
    assert EventType.retrieval_or_index_change.value == "retrieval_or_index_change"
    assert EventType.citation_source_shift.value == "citation_source_shift"
