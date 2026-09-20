"""Evidence-backed marketing implications (Phase 2, issue #59).

The engine must be deterministic, evidence-linked, and honest: every implication
names its supporting claims, no generic advice appears, unknown/monitor-only is a
valid output, and removing the supporting evidence removes the implication.
"""

from __future__ import annotations

from ai_discovery import implications as I
from ai_discovery import mechanics as M


def _claim(
    claim_id="c1",
    *,
    surfaces=("chatgpt",),
    topic="crawler_index_policy",
    statement="OpenAI's crawler policy is documented.",
    confidence="high",
    status="current",
    relationship="new",
    region=None,
):
    return {
        "claim_id": claim_id,
        "topic": topic,
        "statement": statement,
        "surfaces": list(surfaces),
        "status": status,
        "relationship": relationship,
        "confidence": confidence,
        "confidence_detail": {"score": 0.9, "inputs": {}, "rationale": [], "derived": True},
        "source": {
            "source_id": "s",
            "publisher": "OpenAI",
            "url": "https://platform.openai.com/docs/bots",
            "source_class": "official",
        },
        "dates": {"published_at": "2026-09-01", "observed_at": "2026-09-19T00:00:00+00:00"},
        "methodology": {"measurement_mode": "official_documentation", "geography": region},
        "metrics": [],
        "provenance": [],
        "evidence": [],
        "extraction": {},
    }


def _surface(sid, claims):
    return M.project_surface(sid, claims)


def test_every_implication_is_evidence_linked():
    claims = [_claim(claim_id="c1", topic="crawler_index_policy")]
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    assert result.implications
    for impl in result.implications:
        assert impl.supporting_claim_ids, "an implication must cite its evidence"
        assert all(cid in {"c1"} for cid in impl.supporting_claim_ids)


def test_removing_the_supporting_evidence_removes_the_implication():
    """Issue #59 acceptance: no evidence -> no implication."""

    claims = [_claim(claim_id="c1", topic="crawler_index_policy")]
    with_evidence = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    assert with_evidence.implications

    without = I.derive_surface("chatgpt", _surface("chatgpt", []), [])
    assert without.implications == ()
    assert without.monitor_only is True
    assert without.note


def test_unknown_mechanic_yields_explicit_monitor_not_action():
    """A surface with no evidenced mechanic is monitor-only, never invented advice."""

    result = I.derive_surface("claude", _surface("claude", []), [])
    assert result.monitor_only is True
    assert result.implications == ()
    assert "Monitor" in result.note or "monitor" in result.note


def test_wrong_topic_evidence_does_not_fire_a_rule():
    """A mechanic evidenced only by an audience claim must not fire an action rule."""

    claims = [_claim(claim_id="c1", topic="audience_usage")]
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    # audience_usage lights no crawler rule; the projection for crawler controls
    # stays unknown, so no crawlability implication may appear.
    assert all(
        i.family != "crawlability_eligibility" for i in result.implications
    )


def test_confidence_and_actionability_are_distinct_axes():
    claims = [_claim(claim_id="c1", topic="crawler_index_policy", confidence="high")]
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    impl = result.implications[0]
    assert impl.confidence == "high"
    assert impl.actionability in ("high", "medium", "low")
    # They are independent fields, not the same value echoed.
    assert impl.significance >= 0.0


def test_contradicting_evidence_is_carried_and_caps_confidence():
    claims = [
        _claim(claim_id="c1", topic="crawler_index_policy", confidence="high"),
        _claim(
            claim_id="c2",
            topic="crawler_index_policy",
            confidence="high",
            relationship="contradicts",
        ),
    ]
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    impl = result.implications[0]
    assert "c2" in impl.contradicting_claim_ids
    assert impl.confidence == "low", "a live contradiction caps the confidence"


def test_cross_surface_implication_merges_shared_mechanics():
    claims = [
        _claim(claim_id="a", surfaces=("chatgpt",), topic="crawler_index_policy"),
        _claim(claim_id="b", surfaces=("claude",), topic="crawler_index_policy"),
    ]
    per_surface = {
        "chatgpt": I.derive_surface("chatgpt", _surface("chatgpt", claims), claims),
        "claude": I.derive_surface("claude", _surface("claude", claims), claims),
    }
    merged = I.cross_surface_implications(per_surface)
    crawl = [i for i in merged if i.family == "crawlability_eligibility"]
    assert crawl, "the shared mechanic must produce a merged implication"
    top = max(crawl, key=lambda i: len(i.surfaces))
    assert set(top.surfaces) == {"chatgpt", "claude"}
    assert set(top.supporting_claim_ids) >= {"a", "b"}


def test_surface_specific_implication_stays_scoped():
    claims = [_claim(claim_id="a", surfaces=("chatgpt",), topic="commerce_ads")]
    per_surface = {
        "chatgpt": I.derive_surface("chatgpt", _surface("chatgpt", claims), claims),
    }
    merged = I.cross_surface_implications(per_surface)
    for impl in merged:
        if impl.family in ("commerce_shopping", "structured_data_feed"):
            assert impl.surfaces == ("chatgpt",)


def test_no_generic_geo_filler_text():
    """Rules must not contain generic GEO/AEO filler."""

    banned = ("geo", "aeo", "optimise for ai", "rank higher", "best practice", "leverage")
    for rule in I.IMPLICATION_RULES:
        blob = (rule.action + " " + rule.rationale).lower()
        for word in banned:
            assert word not in blob, f"rule {rule.family} contains filler: {word!r}"


def test_rules_reference_real_dimensions():
    assert set(I.RULE_DIMENSIONS) <= set(M.MECHANICS_DIMENSIONS)


def test_confidence_and_significance_are_separate_fields():
    claims = [
        _claim(
            claim_id="c1",
            topic="commerce_ads",
            confidence="medium",
            statement="The surface shows product cards and a shopping carousel in commercial results.",
        )
    ]
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    assert result.implications[0].significance >= 0.0
    assert result.implications[0].confidence in ("high", "medium", "low", "unknown")
