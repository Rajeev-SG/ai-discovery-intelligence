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


def test_generator_caps_at_target():
    bg = BriefGenerator(target_items=2)
    candidates = [item(change=f"c{i}", significance=3.5 + i) for i in range(5)]
    assert len(bg.generate(candidates)) == 2


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
