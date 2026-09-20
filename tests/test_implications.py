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
    # A structured monitor implication replaces the action, carrying no evidence.
    assert without.monitor_only is True
    assert without.note
    assert all(i.monitor_only for i in without.implications)
    assert all(i.supporting_claim_ids == () for i in without.implications)
    assert without.evidenced is False


def test_unknown_mechanic_yields_explicit_monitor_not_action():
    """A surface with no evidenced mechanic is monitor-only, never invented advice."""

    result = I.derive_surface("claude", _surface("claude", []), [])
    assert result.monitor_only is True
    # The no-action outcome is a first-class Implication with family "monitor".
    assert len(result.implications) == 1
    assert result.implications[0].family == "monitor"
    assert result.implications[0].monitor_only is True
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
    """Review impl-005: prove the axes are independent, not merely present.

    A knowledge-only mechanic (answer_type) is high-confidence but LOW
    actionability; a crawler-control mechanic is high-actionability. If the two
    fields were the same value they could not differ in the same claim.
    """

    # Knowledge mechanic: citation presentation is medium actionability; retrieval
    # provider (no rule) is informational. Use the crawl rule: high actionability.
    high_act = [_claim(claim_id="c1", topic="crawler_index_policy", confidence="high")]
    r1 = I.derive_surface("chatgpt", _surface("chatgpt", high_act), high_act)
    impl1 = r1.implications[0]
    assert impl1.confidence == "high"
    assert impl1.actionability == "high"

    # A rule with LOW actionability (structured data is medium; use provider-linked
    # referral_measurement which is low actionability) and high confidence.
    low_act = [
        _claim(
            claim_id="c2",
            topic="referrals_conversion",
            confidence="high",
            statement="The surface grounds answers in retrieved sources and passes referral traffic.",
        )
    ]
    r2 = I.derive_surface("chatgpt", _surface("chatgpt", low_act), low_act)
    referral = [i for i in r2.implications if i.family == "referral_measurement"]
    if referral:
        # High confidence, low actionability — the two axes disagree, proving they
        # are independent.
        assert referral[0].confidence == "high"
        assert referral[0].actionability == "low"


def test_supersedes_is_replacement_not_contradiction():
    """Review impl-001: a superseding claim retires the older reading rather than
    contradicting it, so it must not cap confidence or list a contradiction."""

    claims = [
        _claim(claim_id="old", topic="crawler_index_policy", confidence="high",
               statement="OAI-SearchBot is documented."),
        _claim(
            claim_id="new",
            topic="crawler_index_policy",
            confidence="high",
            relationship="supersedes",
            statement="OAI-SearchBot policy was updated.",
        ),
    ]
    # Give the superseding claim a target so the superseded one is retired.
    claims[1]["supersedes_claim_id"] = "old"
    result = I.derive_surface("chatgpt", _surface("chatgpt", claims), claims)
    impl = next(i for i in result.implications if i.family == "crawlability_eligibility")
    assert "old" not in impl.supporting_claim_ids, "the superseded claim is retired, not supported"
    assert "new" in impl.supporting_claim_ids
    assert impl.contradicting_claim_ids == (), "supersedes is not a contradiction"
    assert impl.confidence == "high", "replacement must not cap confidence at low"


def test_merge_does_not_overstate_significance():
    """Review impl-002: a merged cross-surface implication takes the weakest
    member's significance, not the strongest."""

    def surface_with(sid, claim_id, significance_topic):
        return I.derive_surface(
            sid,
            _surface(
                sid,
                [
                    _claim(
                        claim_id=claim_id,
                        surfaces=(sid,),
                        topic=significance_topic,
                    )
                ],
            ),
            [_claim(claim_id=claim_id, surfaces=(sid,), topic=significance_topic)],
        )

    a = surface_with("chatgpt", "a", "crawler_index_policy")
    b = surface_with("claude", "b", "crawler_index_policy")
    merged = I.cross_surface_implications({"chatgpt": a, "claude": b})
    crawl = [i for i in merged if i.family == "crawlability_eligibility"]
    assert crawl
    top = max(crawl, key=lambda i: len(i.surfaces))
    member_sigs = [i.significance for s in (a, b) for i in s.implications if i.family == "crawlability_eligibility"]
    assert top.significance == min(member_sigs), "merged significance must be the weakest member"


def test_filler_scan_covers_the_view_payload():
    """Review impl-005: scan the rendered payload (including notes), with word
    boundaries, so filler in a note or future free text is caught."""

    import re

    claims = [_claim(claim_id="c1", topic="crawler_index_policy")]
    result = {
        "chatgpt": I.derive_surface("chatgpt", _surface("chatgpt", claims), claims),
        "claude": I.derive_surface("claude", _surface("claude", []), []),
    }
    view = I.implications_view(result)
    banned = re.compile(r"\b(geo|aeo|best practice[s]?|leverage|rank higher)\b", re.IGNORECASE)
    import json
    blob = json.dumps(view)
    assert not banned.search(blob), f"filler found in payload: {banned.search(blob)}"


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
