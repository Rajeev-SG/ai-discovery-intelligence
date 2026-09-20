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
