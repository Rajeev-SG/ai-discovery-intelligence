"""The weekly brief must be produced by the pipeline, deterministically (issue #48).

`docs/PIPELINES.md` lists `weekly_exec_brief` and `brief.py` implements it, but
nothing built one in production, so `GET /brief` was permanently empty. These
tests pin the wiring: real change events + their grounding claims become a
gated, deterministic brief with no model in the loop.
"""

from __future__ import annotations

import datetime as dt

from ai_discovery.brief import BriefGenerator
from ai_discovery.brief_wiring import brief_item_from_event, generate_brief_items


def _claim(confidence="medium", topic="citations_sources"):
    return {
        "claim_id": "c1",
        "topic": topic,
        "confidence": confidence,
        "surfaces": ["chatgpt"],
        "status": "current",
        "value": [{"value_number": 16.8}],
        "statement": "Reddit is the most-cited domain in ChatGPT answers.",
    }


def _event(**kw):
    base = {
        "id": "e1",
        "event_type": "citation_source_shift",
        "title": "Reddit is the most-cited domain in ChatGPT answers.",
        "surfaces": ["chatgpt"],
        "claims": ["c1"],
        "effective_from": None,
        "published_at": "2026-09-18T00:00:00+00:00",
        "observed_at": "2026-09-19T00:00:00+00:00",
    }
    return {**base, **kw}


def test_high_confidence_material_event_becomes_an_item():
    items = generate_brief_items([_event()], {"c1": _claim()})
    assert len(items) == 1
    assert items[0].evidence_ids == ["c1"]
    assert items[0].surfaces == ["chatgpt"]
    assert items[0].why_it_matters and items[0].agency_action


def test_low_confidence_event_is_excluded():
    items = generate_brief_items([_event()], {"c1": _claim(confidence="low")})
    assert items == []


def test_event_without_a_grounding_claim_is_excluded():
    items = generate_brief_items([_event()], {})
    assert items == []


def test_framing_is_deterministic_per_event_type():
    """The same event type always yields the same framing; no model involved."""

    a = brief_item_from_event(_event(), _claim())
    b = brief_item_from_event(_event(), _claim())
    assert (a.why_it_matters, a.agency_action) == (b.why_it_matters, b.agency_action)
    other = brief_item_from_event(_event(event_type="crawler_policy"), _claim())
    assert other.why_it_matters != a.why_it_matters


def test_window_excludes_old_events_but_keeps_recent():
    old = _event(id="e-old", published_at="2026-06-01T00:00:00+00:00")
    recent = _event(id="e-new", published_at="2026-09-18T00:00:00+00:00")
    ref = dt.datetime(2026, 9, 19, tzinfo=dt.UTC)
    items = generate_brief_items([old, recent], {"c1": _claim()}, reference=ref)
    assert len(items) == 1
    assert "e-new" not in items[0].evidence_ids  # evidence_ids are claim ids
    unwindowed = generate_brief_items([old, recent], {"c1": _claim()})
    assert len(unwindowed) == 2


def test_brief_is_capped_by_the_hard_max():
    events = [_event(id=f"e{i}") for i in range(20)]
    items = generate_brief_items(events, {"c1": _claim()}, generator=BriefGenerator())
    assert len(items) <= 5
