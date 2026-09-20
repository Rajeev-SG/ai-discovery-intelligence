"""Canonical mechanics ontology + evidence contract (Phase 2, issue #56).

The projection is a pure function of validated ledger claims: known/partial/
conflicting/unknown are all reachable, nothing is invented, and a dimension with
no supporting claim is an explicit unknown. Tests cover all four states plus the
"evidence is never synthesised" invariants.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from ai_discovery import mechanics as M


def _claim(
    claim_id="c1",
    *,
    surfaces=("chatgpt",),
    topic="crawler_index_policy",
    statement="OpenAI exposes OAI-SearchBot and GPTBot robots.txt tags.",
    source_class="official",
    publisher="OpenAI",
    url="https://platform.openai.com/docs/bots",
    confidence="high",
    status="current",
    relationship="new",
    supersedes=None,
    geography=None,
    observed_at="2026-09-19T12:00:00+00:00",
    published_at="2026-09-17",
):
    return {
        "claim_id": claim_id,
        "topic": topic,
        "statement": statement,
        "surfaces": list(surfaces),
        "status": status,
        "relationship": relationship,
        "supersedes_claim_id": supersedes,
        "confidence": confidence,
        "confidence_detail": {"score": 0.9, "inputs": {}, "rationale": [], "derived": True},
        "source": {
            "source_id": "openai-platform-bots",
            "publisher": publisher,
            "url": url,
            "source_class": source_class,
        },
        "dates": {"published_at": published_at, "observed_at": observed_at},
        "methodology": {
            "measurement_mode": "official_documentation",
            "methodology_notes": "Vendor crawler documentation.",
            "limitations": ["Covers crawler policy only."],
            "geography": geography,
        },
        "metrics": [],
        "provenance": [],
        "evidence": [],
    }


# --------------------------------------------------------------------------- #
# Contract completeness and unknowns
# --------------------------------------------------------------------------- #


def test_projection_covers_every_dimension_in_order():
    m = M.project_surface("chatgpt", [])
    assert [d.dimension for d in m.dimensions] == list(M.MECHANICS_DIMENSIONS)
    assert len(m.dimensions) == 13


def test_no_claims_yields_all_unknown_with_explicit_notes():
    m = M.project_surface("deepseek-chat", [])
    cov = m.coverage()
    assert cov["unknown"] == 13
    assert m.evidenced_dimension_count() == 0
    # Unknown is an answer: every unknown dimension carries a note.
    for d in m.dimensions:
        assert d.state == "unknown"
        assert d.note


def test_registry_metadata_is_never_used_as_evidence():
    # A surface projected with zero claims stays fully unknown even though the
    # registry would have retrieval_status=partially_documented for chatgpt.
    m = M.project_surface("chatgpt", [])
    assert m.state_of("retrieval_provider") == "unknown"
    assert m.state_of("crawling_indexing_controls") == "unknown"


# --------------------------------------------------------------------------- #
# known / partially_known / conflicting / unknown
# --------------------------------------------------------------------------- #


def test_known_dimension_from_official_claim():
    m = M.project_surface("chatgpt", [_claim()])
    d = m.dimension("crawling_indexing_controls")
    assert d.state == "known"
    a = d.assertions[0]
    assert a.evidence[0].source_class == "official"
    assert a.evidence[0].evidence_class == "official_documentation"
    assert d.evidence_ids == ("c1",)


def test_partially_known_from_watch_claim():
    m = M.project_surface("chatgpt", [_claim(status="watch")])
    assert m.state_of("crawling_indexing_controls") == "partially_known"


def test_conflicting_from_contradiction():
    a = _claim(claim_id="c1")
    b = _claim(claim_id="c2", relationship="contradicts", supersedes="c1")
    m = M.project_surface("chatgpt", [a, b])
    d = m.dimension("crawling_indexing_controls")
    assert d.state == "conflicting"
    assert d.assertions[0].conflict_note is not None
    assert set(d.evidence_ids) == {"c1", "c2"}


def test_non_mechanics_topic_never_lights_a_mechanics_dimension():
    # audience_usage is a non-mechanics topic: it must light NO dimension, so a
    # market-share claim can never masquerade as a "how discovery works" fact.
    m = M.project_surface("chatgpt", [_claim(topic="audience_usage")])
    assert m.evidenced_dimension_count() == 0
    for d in m.dimensions:
        assert d.state == "unknown"


def test_claim_for_other_surface_does_not_leak():
    m = M.project_surface("claude", [_claim(surfaces=("chatgpt",))])
    assert m.evidenced_dimension_count() == 0


# --------------------------------------------------------------------------- #
# Evidence class separation (issue #56: keep classes distinct)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "source_class,expected",
    [
        ("official", "official_documentation"),
        ("market_telemetry", "independent_research"),
        ("visibility_research", "independent_research"),
        ("controlled_observation", "controlled_observation"),
    ],
)
def test_evidence_class_mapping(source_class, expected):
    assert M.evidence_class_for(source_class) == expected


def test_evidence_class_mismatch_is_rejected():
    ev = M.MechanicsEvidence(
        claim_id="c1",
        source_class="official",
        evidence_class="official_documentation",
        confidence="high",
    )
    assert ev.evidence_class == "official_documentation"
    with pytest.raises(ValidationError):
        M.MechanicsEvidence(
            claim_id="c1",
            source_class="official",
            evidence_class="independent_research",
            confidence="high",
        )


def test_controlled_observation_is_distinct_from_vendor_documentation():
    obs = _claim(claim_id="obs", source_class="controlled_observation", publisher="Agency")
    doc = _claim(claim_id="doc", source_class="official")
    m = M.project_surface("chatgpt", [obs, doc])
    classes = {e.evidence_class for e in m.dimension("crawling_indexing_controls").assertions[0].evidence}
    assert classes == {"controlled_observation", "official_documentation"}


# --------------------------------------------------------------------------- #
# Schema guards: nothing fabricated, no blanks
# --------------------------------------------------------------------------- #


def test_unknown_state_cannot_carry_assertions():
    with pytest.raises(ValidationError):
        M.DimensionState(
            dimension="answer_type",
            state="unknown",
            assertions=(
                M.MechanicsAssertion(
                    statement="x",
                    state="known",
                    evidence=(
                        M.MechanicsEvidence(
                            claim_id="c",
                            source_class="official",
                            evidence_class="official_documentation",
                            confidence="high",
                        ),
                    ),
                ),
            ),
            note="n",
        )


def test_known_state_requires_evidence():
    with pytest.raises(ValidationError):
        M.DimensionState(dimension="answer_type", state="known", assertions=())


def test_incomplete_projection_is_rejected():
    m = M.project_surface("chatgpt", [])
    payload = m.model_dump()
    payload["dimensions"] = payload["dimensions"][:-1]
    with pytest.raises(ValidationError):
        M.SurfaceMechanics(**payload)


def test_invalid_dimension_name_rejected():
    with pytest.raises(ValidationError):
        M.DimensionState(dimension="not_a_dimension", state="unknown", note="n")


# --------------------------------------------------------------------------- #
# Marketer-safe serialisation: no private data
# --------------------------------------------------------------------------- #


def test_view_exposes_no_private_snapshot_fields():
    m = M.project_surface("chatgpt", [_claim()])
    view = M.mechanics_view(m)
    blob = repr(view)
    for forbidden in ("snapshot_path", "capture_hash", "/var/", "/private/"):
        assert forbidden not in blob
    # crawler_index_policy maps to crawling_indexing_controls, freshness_recrawl
    # and marketer_controllable_inputs -> 3 known, 10 unknown.
    assert view["coverage"]["unknown"] == 10
    assert view["evidenced_dimension_count"] == 3


def test_view_carries_the_evidence_contract_fields():
    m = M.project_surface("chatgpt", [_claim()])
    ev = M.mechanics_view(m)["dimensions"][3]["assertions"][0]["evidence"][0]
    for key in (
        "claim_id",
        "source_class",
        "evidence_class",
        "publisher",
        "url",
        "published_at",
        "observed_at",
        "confidence",
        "methodology_notes",
    ):
        assert key in ev


def test_projection_does_not_mutate_claims():
    claims = [_claim()]
    snapshot = copy.deepcopy(claims)
    M.project_surface("chatgpt", claims)
    assert claims == snapshot


# --------------------------------------------------------------------------- #
# Surface alias resolution (real claims name a surface as the page wrote it)
# --------------------------------------------------------------------------- #


def test_deepseek_alias_attaches_claim_to_canonical_surface():
    from ai_discovery.registry import resolve_surface_id

    assert resolve_surface_id("deepseek") == "deepseek-chat"
    assert resolve_surface_id("naver-ai-tab") == "naver-ai"
    m = M.project_surface("deepseek-chat", [_claim(surfaces=("deepseek",))])
    assert m.evidenced_dimension_count() == 3  # crawler_index_policy maps to 3 dims


def test_non_surface_values_are_not_coerced():
    from ai_discovery.registry import resolve_surface_id

    # A cited domain and a category are not surfaces: identity, never coerced.
    assert resolve_surface_id("reddit") == "reddit"
    assert resolve_surface_id("answer-engines") == "answer-engines"
    m = M.project_surface("chatgpt", [_claim(surfaces=("reddit",))])
    assert m.evidenced_dimension_count() == 0


def test_unmapped_diagnostic_is_alias_aware():
    claims = [_claim(surfaces=("deepseek",)), _claim(claim_id="c2", surfaces=("reddit",))]
    unmapped = M.unmapped_claim_surfaces(["deepseek-chat"], claims)
    assert "deepseek" not in unmapped  # aliased to a real surface
    assert unmapped["reddit"] == ["c2"]


def test_dimension_with_no_topic_mapping_is_always_unknown():
    # social_community_retrieval has no topic mapping: a coarse citation-share
    # claim must not light it. It stays an honest unknown.
    m = M.project_surface("chatgpt", [_claim(topic="citations_sources")])
    assert m.state_of("social_community_retrieval") == "unknown"
    assert m.state_of("citation_presentation") == "known"
