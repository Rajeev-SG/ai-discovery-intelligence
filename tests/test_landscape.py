"""Marketer-first landscape + mechanics comparison (Phase 2, issue #60)."""

from __future__ import annotations

from ai_discovery import landscape as L
from ai_discovery import mechanics as M
from ai_discovery.registry import SurfaceConfig, SurfacesConfig


def _registry() -> SurfacesConfig:
    def s(sid, name, vendor, tier="core_global", type_="conversational_assistant", regions=("global",)):
        return SurfaceConfig(
            id=sid,
            vendor=vendor,
            name=name,
            family=name,
            type=type_,
            tier=tier,
            regions=list(regions),
            distribution=["web"],
            discovery_modes=["search"],
            retrieval_status="partially_documented",
            official_urls=[f"https://{sid}.example/"],
        )

    return SurfacesConfig(
        surfaces=[
            s("chatgpt", "ChatGPT", "OpenAI"),
            s("claude", "Claude", "Anthropic"),
            s("deepseek-chat", "DeepSeek Chat", "DeepSeek", tier="core_china"),
            s("doubao", "Doubao", "ByteDance", tier="core_china"),
        ]
    )


def _claim(claim_id="c1", *, surfaces=("chatgpt",), topic="crawler_index_policy",
           statement="OpenAI documents OAI-SearchBot and its robots.txt controls.",
           confidence="high", value_number=None, label="L", value_text=None):
    metrics = []
    if value_number is not None or value_text is not None:
        metrics = [{"metric_id": "m1", "label": label, "value_number": value_number,
                    "value_text": value_text, "unit": "%", "scope": label}]
    return {
        "claim_id": claim_id, "topic": topic, "statement": statement,
        "surfaces": list(surfaces), "status": "current", "relationship": "new",
        "confidence": confidence,
        "confidence_detail": {"score": 0.9, "inputs": {}, "rationale": [], "derived": True},
        "source": {"source_id": "s", "publisher": "P", "url": "https://e.test",
                   "source_class": "official"},
        "dates": {"published_at": "2026-09-01", "observed_at": "2026-09-19T00:00:00+00:00"},
        "methodology": {"measurement_mode": "m", "geography": None},
        "metrics": metrics, "provenance": [], "evidence": [], "extraction": {},
    }


def _projection(registry, claims):
    proj = M.project_all(registry.ids(), claims)
    return proj


def test_landscape_only_contains_known_registry_surfaces():
    registry = _registry()
    rows = L.build_landscape(registry, _projection(registry, []), [], ids=("chatgpt", "not-real"))
    assert [r.id for r in rows] == ["chatgpt"], "a curated id absent from the registry is skipped, not faked"


def test_landscape_reports_zero_coverage_when_no_evidence():
    registry = _registry()
    row = L.build_landscape(registry, _projection(registry, []), [])[0]
    assert row.evidenced_dimensions == 0
    assert row.coverage["unknown"] == row.dimension_count
    assert "not" in row.relevance.lower() or "No evidenced" in row.relevance


def test_landscape_coverage_reflects_evidenced_mechanics():
    registry = _registry()
    claims = [_claim(claim_id="c1", surfaces=("chatgpt",))]
    row = L.build_landscape(registry, _projection(registry, claims), claims, ids=("chatgpt",))[0]
    assert row.evidenced_dimensions >= 1
    assert row.coverage["known"] >= 1


def test_reach_is_the_surfaces_own_metric_not_a_joint_claims():
    """A joint multi-surface claim must not attribute another surface's figure."""

    registry = _registry()
    claims = [
        _claim(
            claim_id="joint",
            surfaces=("doubao", "deepseek-chat"),
            topic="audience_usage",
            statement="Doubao and DeepSeek usage.",
            value_number=144.6,
            label="Doubao average usage time",
        ),
        _claim(
            claim_id="own",
            surfaces=("deepseek-chat",),
            topic="audience_usage",
            statement="DeepSeek market share.",
            value_number=0.02,
            label="DeepSeek market share",
        ),
    ]
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, claims), claims)}
    ds = rows["deepseek-chat"]
    assert ds.reach_claim_id == "own"
    assert "0.02" in (ds.reach_metric or "")


def test_reach_is_none_when_no_usage_evidence():
    registry = _registry()
    row = L.build_landscape(registry, _projection(registry, []), [], ids=("claude",))[0]
    assert row.reach_metric is None


def test_comparison_keeps_unknown_explicit():
    registry = _registry()
    comparison = L.build_comparison(["chatgpt", "claude"], _projection(registry, []))
    for row in comparison:
        # No evidence at all: every cell is an explicit unknown.
        assert all(c.unknown for c in row.cells.values())


def test_comparison_cell_carries_evidence_link():
    registry = _registry()
    claims = [_claim(claim_id="c1", surfaces=("chatgpt",))]
    comparison = L.build_comparison(["chatgpt"], _projection(registry, claims))
    cell = next(r for r in comparison if r.dimension == "crawling_indexing_controls").cells["chatgpt"]
    assert cell.unknown is False
    assert cell.claim_id == "c1"
    assert cell.evidence_class == "official_documentation"
    assert cell.confidence == "high"


def test_comparison_dims_are_canonical():
    assert set(L.COMPARISON_DIMENSIONS) <= set(M.MECHANICS_DIMENSIONS)
    assert set(L.LANDSCAPE_IDS)  # non-empty curated set


def test_reach_is_none_when_a_joint_claim_names_neither_surface():
    """Review: a joint claim whose metric names neither surface yields no figure."""

    registry = _registry()
    joint = _claim(
        claim_id="joint",
        surfaces=("doubao", "deepseek-chat"),
        topic="audience_usage",
        statement="Both assistants gained users.",
        value_number=5.0,
        label="combined assistant users",
    )
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, [joint]), [joint])}
    assert rows["doubao"].reach_metric is None
    assert rows["deepseek-chat"].reach_metric is None


def test_vendor_ambiguous_joint_claim_is_not_attributed():
    """Review: a joint Google claim labelled 'Google AI users' must not be
    attributed to either Gemini or AI Mode (the vendor token is ambiguous)."""

    def g(sid, name):
        return SurfaceConfig(
            id=sid, vendor="Google", name=name, family=name,
            type="conversational_assistant", tier="core_global",
            regions=["global"], distribution=["web"], discovery_modes=["search"],
            retrieval_status="partially_documented", official_urls=[f"https://{sid}.example/"],
        )

    registry = SurfacesConfig(surfaces=[g("google-gemini", "Gemini"), g("google-ai-mode", "Google Search AI Mode")])
    joint = _claim(
        claim_id="google-joint",
        surfaces=("google-gemini", "google-ai-mode"),
        topic="audience_usage",
        statement="Google AI users grew.",
        value_number=100.0,
        label="Google AI users",
    )
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, [joint]), [joint])}
    assert rows["google-gemini"].reach_metric is None
    assert rows["google-ai-mode"].reach_metric is None


# --------------------------------------------------------------------------- #
# Issue #69 P0: reach is a population figure, not any audience_usage number
# --------------------------------------------------------------------------- #


def test_reach_excludes_attitude_survey_metrics():
    """A 'percentage of AI users who dislike chatbot ads' survey metric is an
    attitude measure, not DeepSeek's reach — no figure rather than a wrong one."""

    registry = _registry()
    claim = _claim(
        claim_id="deepseek-attitude",
        surfaces=("deepseek-chat",),
        topic="audience_usage",
        statement="A survey found 4 in 10 AI users dislike chatbot ads.",
        value_number=40.0,
        label="percentage of AI users who dislike chatbot ads",
    )
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, [claim]), [claim])}
    assert rows["deepseek-chat"].reach_metric is None


def test_reach_excludes_engagement_duration_metrics():
    """Doubao's 144.6 minutes is time spent (engagement intensity), not reach."""

    registry = _registry()
    claim = _claim(
        claim_id="doubao-duration",
        surfaces=("doubao",),
        topic="audience_usage",
        statement="Doubao users spend an average of 144.6 minutes per month.",
        value_number=144.6,
        label="average monthly usage time",
    )
    claim["metrics"][0]["unit"] = "minutes"
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, [claim]), [claim])}
    assert rows["doubao"].reach_metric is None


def test_reach_still_accepts_market_share_and_user_counts():
    """Genuine audience-size metrics remain eligible for the reach figure."""

    registry = _registry()
    share = _claim(
        claim_id="share",
        surfaces=("chatgpt",),
        topic="audience_usage",
        statement="ChatGPT holds 79.4% of AI chatbot traffic.",
        value_number=79.4,
        label="market share",
    )
    users = _claim(
        claim_id="users",
        surfaces=("doubao",),
        topic="audience_usage",
        statement="Doubao reports 150 million monthly active users.",
        value_number=150000000,
        label="monthly active users",
    )
    users["metrics"][0]["unit"] = "users"
    claim_metrics = [share, users]
    rows = {r.id: r for r in L.build_landscape(registry, _projection(registry, claim_metrics), claim_metrics)}
    assert rows["chatgpt"].reach_metric == "market share: 79.4 %"
    assert rows["doubao"].reach_metric == "monthly active users: 150,000,000 users"
