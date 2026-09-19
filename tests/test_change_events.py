import datetime as dt

import pytest
from pydantic import ValidationError

from ai_discovery.change_events import ChangeEvent, EventStore, EventType


def ev(**kw):
    defaults: dict = {
        "event_type": EventType.citation_source_shift,
        "title": "Synthetic unit fixture, not product proof",
        "description": "fixture",
        "surfaces": ["chatgpt"],
        "claims": ["c1"],
        "evidence_urls": ["https://example.com/s"],
        "observed_at": dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
        "published_at": dt.datetime(2026, 8, 26, tzinfo=dt.UTC),
        "dedupe_key": "test-key",
    }
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
    with pytest.raises(ValidationError):
        e.title = "mutated"


def test_supersedes_field():
    e = ev(id="y", supersedes="x")
    assert e.supersedes == "x"


def test_type_values():
    assert EventType.product_launch.value == "product_launch"
    assert EventType.retrieval_or_index_change.value == "retrieval_or_index_change"
    assert EventType.citation_source_shift.value == "citation_source_shift"


# --- issue #27: corrections survive dedupe; event-time windows -------------- #


def test_correction_with_shared_dedupe_key_survives():
    """Two events sharing a dedupe key, where the later is a correction, both survive."""

    store = EventStore()
    store.append(
        ev(
            id="orig",
            event_type=EventType.audience_shift,
            dedupe_key="syndicated-1",
            published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC),
        )
    )
    store.append(
        ev(
            id="corr",
            event_type=EventType.correction_retraction,
            dedupe_key="syndicated-1",
            supersedes="orig",
            published_at=dt.datetime(2026, 9, 5, tzinfo=dt.UTC),
        )
    )
    ids = [e.id for e in store.dedupe()]
    assert "orig" in ids and "corr" in ids, ids


def test_timeline_returns_original_then_correction_in_order():
    store = EventStore()
    store.append(
        ev(id="orig", dedupe_key="k", published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC))
    )
    store.append(
        ev(
            id="corr",
            event_type=EventType.correction_retraction,
            dedupe_key="k",
            supersedes="orig",
            published_at=dt.datetime(2026, 9, 5, tzinfo=dt.UTC),
        )
    )
    assert [e.id for e in store.timeline()] == ["orig", "corr"]


def test_superseding_non_correction_event_also_survives():
    """Any event carrying ``supersedes`` is protected, not only corrections."""

    store = EventStore()
    store.append(ev(id="v1", dedupe_key="same", published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC)))
    store.append(
        ev(
            id="v2",
            event_type=EventType.audience_shift,
            dedupe_key="same",
            supersedes="v1",
            published_at=dt.datetime(2026, 9, 2, tzinfo=dt.UTC),
        )
    )
    assert {e.id for e in store.dedupe()} == {"v1", "v2"}


def test_plain_syndicated_duplicates_are_still_deduplicated():
    """The correction rule must not disable ordinary syndication dedupe."""

    store = EventStore()
    store.append(ev(id="a", dedupe_key="dup", published_at=dt.datetime(2026, 9, 1, tzinfo=dt.UTC)))
    store.append(ev(id="b", dedupe_key="dup", published_at=dt.datetime(2026, 9, 2, tzinfo=dt.UTC)))
    assert [e.id for e in store.dedupe()] == ["a"]


def test_in_window_uses_effective_time_not_observation_time():
    """A study published last year but ingested this week is not in this week's window."""

    old_study = ev(
        id="old",
        published_at=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),  # ingested this week
        dedupe_key=None,
    )
    new_change = ev(
        id="new",
        published_at=dt.datetime(2026, 9, 15, tzinfo=dt.UTC),
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
        dedupe_key=None,
    )
    window = EventStore.in_window(
        [old_study, new_change],
        window_start=dt.datetime(2026, 9, 10, tzinfo=dt.UTC),
        window_end=dt.datetime(2026, 9, 17, tzinfo=dt.UTC),
    )
    assert [e.id for e in window] == ["new"]


def test_in_window_prefers_effective_from_when_stated():
    e = ev(
        id="x",
        effective_from=dt.datetime(2026, 9, 12, tzinfo=dt.UTC),
        published_at=dt.datetime(2026, 8, 1, tzinfo=dt.UTC),
        dedupe_key=None,
    )
    window = EventStore.in_window(
        [e],
        window_start=dt.datetime(2026, 9, 10, tzinfo=dt.UTC),
        window_end=dt.datetime(2026, 9, 17, tzinfo=dt.UTC),
    )
    assert [e2.id for e2 in window] == ["x"]
