from ai_discovery.brief import (
    BriefGenerator,
    BriefItem,
    ConfidenceLabel,
    ConfidenceScorer,
    SignificanceScorer,
)


def item(**kw):
    defaults: dict = {
        "change": "test",
        "why_it_matters": "test",
        "agency_action": "monitor",
        "confidence": ConfidenceLabel.MEDIUM,
        "significance": 3.5,
        "evidence_ids": ["e1"],
        "surfaces": ["chatgpt"],
    }
    return BriefItem(**{**defaults, **kw})


def test_confidence_scorer_weights_sum():
    cs = ConfidenceScorer()
    total = (
        cs.source_authority
        + cs.methodology_transparency
        + cs.sample_strength
        + cs.recency
        + cs.geography_fit
        + cs.corroboration
        + cs.directness
    )
    assert abs(total - 1.0) < 0.01


def test_significance_scorer_weights_sum():
    ss = SignificanceScorer()
    total = (
        ss.reach
        + ss.commercial_intent
        + ss.magnitude
        + ss.breadth
        + ss.persistence
        + ss.actionability
    )
    assert abs(total - 1.0) < 0.01


def test_confidence_labels():
    cs = ConfidenceScorer()
    assert cs.label(0.9) == ConfidenceLabel.HIGH
    assert cs.label(0.75) == ConfidenceLabel.MEDIUM_HIGH
    assert cs.label(0.6) == ConfidenceLabel.MEDIUM
    assert cs.label(0.3) == ConfidenceLabel.LOW


def test_significance_scale_0_to_5():
    ss = SignificanceScorer()
    assert (
        ss.score(
            reach=1.0,
            commercial_intent=1.0,
            magnitude=1.0,
            breadth=1.0,
            persistence=1.0,
            actionability=1.0,
        )
        == 5.0
    )
    assert (
        ss.score(
            reach=0.0,
            commercial_intent=0.0,
            magnitude=0.0,
            breadth=0.0,
            persistence=0.0,
            actionability=0.0,
        )
        == 0.0
    )
    assert ss.score() == 2.5  # all 0.5 defaults


def test_generator_includes_material():
    bg = BriefGenerator()
    candidates = [
        item(change="material change", significance=4.0, confidence=ConfidenceLabel.MEDIUM),
        item(change="trivial ui tweak", significance=1.5, confidence=ConfidenceLabel.HIGH),
    ]
    result = bg.generate(candidates)
    assert len(result) == 1
    assert result[0].change == "material change"


def test_generator_excludes_low_confidence():
    bg = BriefGenerator()
    candidates = [item(change="x", significance=4.5, confidence=ConfidenceLabel.LOW)]
    assert bg.generate(candidates) == []


def test_generator_watch_item():
    bg = BriefGenerator()
    candidates = [
        item(change="x", significance=4.6, confidence=ConfidenceLabel.LOW, is_watch_item=True)
    ]
    result = bg.generate(candidates)
    assert len(result) == 1
    assert result[0].is_watch_item


def test_target_is_a_soft_quality_gate_not_dead_config():
    """Issue #28B F1: target_items must change behaviour, not be unused.

    Two generators differing only in target_items must produce different output
    for a candidate set whose items straddle the beyond-target bar.
    """

    # Items: 3 strong (>= 4.5 beyond-bar) and 2 weaker (>= 3.5 normal bar).
    cands = [
        item(change="strong1", significance=5.0),
        item(change="strong2", significance=4.9),
        item(change="strong3", significance=4.6),
        item(change="weak1", significance=3.9),
        item(change="weak2", significance=3.6),
    ]
    # target 5 -> all 5 qualify at the normal bar.
    wide = BriefGenerator(target_items=5, max_items=5)
    assert len(wide.generate(cands)) == 5
    # target 3 -> the two weaker items fall below the beyond-target bar.
    narrow = BriefGenerator(target_items=3, max_items=5)
    out = narrow.generate(cands)
    assert len(out) == 3, [x.change for x in out]
    assert {x.change for x in out} == {"strong1", "strong2", "strong3"}


def test_default_config_can_emit_the_hard_max():
    """Regression: the original bug — default config could never reach max_items."""

    bg = BriefGenerator()  # target_items=3 (soft), max_items=5 (hard)
    cands = [item(change=f"c{i}", significance=5.0 - i * 0.01) for i in range(5)]
    out = bg.generate(cands)
    assert len(out) == 5, "default config must be able to emit max_items when warranted"


def test_target_is_soft_and_max_is_hard():
    """Issue #28B: target_items is a soft target; max_items is the hard ceiling."""

    candidates = [item(change=f"c{i}", significance=3.5 + i) for i in range(6)]
    # target below the material available -> emit more than the target, up to max.
    bg = BriefGenerator(target_items=3, max_items=5)
    out = bg.generate(candidates)
    assert len(out) == 5, "should use the hard maximum when more material qualifies"
    assert out[0].significance == max(c.significance for c in candidates)

    # The hard ceiling is never exceeded even when everything qualifies.
    strong = [item(change=f"c{i}", significance=5.0) for i in range(9)]
    bg2 = BriefGenerator(target_items=2, max_items=3)
    assert len(bg2.generate(strong)) == 3

    # Fewer qualifying items than the target is fine (soft, not a floor).
    bg3 = BriefGenerator(target_items=3, max_items=5)
    assert len(bg3.generate([item(change="only", significance=4.0)])) == 1


def test_watch_item_cannot_displace_corroborated_material():
    """A watch item never takes a slot corroborated material wanted."""

    bg = BriefGenerator(target_items=3, max_items=3)
    corroborated = [item(change=f"c{i}", significance=4.0 + i) for i in range(3)]
    watch = item(change="uncorroborated", significance=4.9, is_watch_item=True)
    out = bg.generate([*corroborated, watch])
    assert len(out) == 3
    assert not any(x.is_watch_item for x in out), "watch item displaced corroborated material"


def test_single_watch_item_fills_a_free_slot():
    """When corroborated material leaves room, exactly one watch item may appear."""

    bg = BriefGenerator(target_items=3, max_items=4)
    corrob = [item(change="c1", significance=4.0)]
    watches = [
        item(change="w1", significance=4.6, is_watch_item=True),
        item(change="w2", significance=4.7, is_watch_item=True),
    ]
    out = bg.generate([*corrob, *watches])
    assert sum(1 for x in out if x.is_watch_item) == 1
    assert out[0].change == "c1"  # corroborated material still leads


def test_generator_caps_at_max():
    bg = BriefGenerator(target_items=5, max_items=3)
    candidates = [item(change=f"c{i}", significance=3.5 + i) for i in range(5)]
    assert len(bg.generate(candidates)) == 3


def test_generator_zero_items_valid():
    bg = BriefGenerator()
    assert bg.generate([item(change="trivial", significance=1.0)]) == []


def test_generator_sorts_by_significance():
    bg = BriefGenerator(target_items=3)
    candidates = [
        item(change="low", significance=3.5),
        item(change="high", significance=4.8),
        item(change="mid", significance=4.0),
    ]
    result = bg.generate(candidates)
    assert [i.change for i in result] == ["high", "mid", "low"]


# --- issue #27: the brief reasons over event time, not ingestion time ------- #

import datetime as dt


def test_brief_excludes_newly_ingested_old_study_and_includes_new_event():
    """An old study first ingested this week is not this week's change."""

    bg = BriefGenerator(target_items=3, max_items=5)
    old_study = item(
        change="2024 study, ingested this week",
        significance=5.0,
        published_at=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
    )
    new_event = item(
        change="genuinely new this week",
        significance=4.2,
        published_at=dt.datetime(2026, 9, 15, tzinfo=dt.UTC),
        observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
    )
    out = bg.generate(
        [old_study, new_event],
        window_start=dt.datetime(2026, 9, 10, tzinfo=dt.UTC),
        window_end=dt.datetime(2026, 9, 17, tzinfo=dt.UTC),
    )
    assert [x.change for x in out] == ["genuinely new this week"]


def test_windowed_brief_drops_undated_items():
    """Without an effective time an item cannot be claimed as this week's change."""

    bg = BriefGenerator(target_items=3, max_items=5)
    undated = item(change="undated", significance=5.0)
    out = bg.generate(
        [undated],
        window_start=dt.datetime(2026, 9, 10, tzinfo=dt.UTC),
        window_end=dt.datetime(2026, 9, 17, tzinfo=dt.UTC),
    )
    assert out == []


def test_no_window_keeps_previous_behaviour():
    bg = BriefGenerator(target_items=3, max_items=5)
    out = bg.generate([item(change="x", significance=4.0)])
    assert len(out) == 1


def test_build_weekly_brief_is_the_product_entry_point():
    """The real weekly path applies the window; a caller cannot forget it."""

    from ai_discovery.brief import build_weekly_brief, weekly_window

    ref = dt.datetime(2026, 9, 17, tzinfo=dt.UTC)
    old = item(
        change="old study ingested this week",
        significance=5.0,
        published_at=dt.datetime(2024, 1, 1, tzinfo=dt.UTC),
    )
    new = item(
        change="this week's change",
        significance=4.0,
        published_at=dt.datetime(2026, 9, 15, tzinfo=dt.UTC),
    )
    out = build_weekly_brief([old, new], reference=ref)
    assert [x.change for x in out] == ["this week's change"]
    start, end = weekly_window(ref)
    assert (end - start).days == 7
