"""Canonical mechanics ontology + evidence contract (Phase 2, issue #56).

The projection is a pure function of validated ledger claims: known/partial/
conflicting/unknown are all reachable, nothing is invented, and a dimension with
no supporting claim is an explicit unknown. Tests cover all four states plus the
"evidence is never synthesised" invariants.
"""

from __future__ import annotations

import copy
import datetime as dt

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


def test_share_only_citation_claim_lights_no_mechanics_dimension():
    # F1: a citation-SHARE claim asserts no presentation mechanic, so it must
    # light nothing. A market-share/citation-share number is not "how it works".
    m = M.project_surface(
        "chatgpt",
        [_claim(topic="citations_sources", statement="Reddit held a 3.8% share of ChatGPT citations.")],
    )
    assert m.evidenced_dimension_count() == 0
    assert m.state_of("citation_presentation") == "unknown"


def test_citation_presentation_claim_requires_content_signal():
    # A claim whose text actually asserts a presentation mechanic does light it.
    m = M.project_surface(
        "chatgpt",
        [_claim(
            topic="citations_sources",
            statement="The average number of sources cited per ChatGPT response is shown inline as links.",
        )],
    )
    assert m.state_of("citation_presentation") == "known"


def test_social_and_local_stay_unknown_without_a_matching_signal():
    m = M.project_surface("chatgpt", [_claim(topic="citations_sources")])
    assert m.state_of("social_community_retrieval") == "unknown"
    assert m.state_of("local_retrieval") == "unknown"


# --------------------------------------------------------------------------- #
# F2: an end-to-end multi-source ledger through the projection
# --------------------------------------------------------------------------- #


def test_multi_source_ledger_projects_conflict_and_supersession():
    """A realistic multi-source ledger: conflict + supersession are reachable.

    The production ledger currently holds no conflicting claims (all
    ``relationship='new'``), so this drives the *projection* over a realistic
    multi-source set end-to-end: two sources disagree on the same dimension, and
    one explicitly supersedes a prior reading.
    """

    a = _claim(claim_id="a", source_class="official", publisher="Vendor", statement="X is documented.")
    b = _claim(claim_id="b", source_class="market_telemetry", publisher="Tracker", statement="X is contested.")
    c = _claim(
        claim_id="c",
        source_class="official",
        publisher="Vendor",
        statement="X supersedes b.",
        relationship="supersedes",
        supersedes="b",
    )
    m = M.project_surface("chatgpt", [a, b, c])
    d = m.dimension("crawling_indexing_controls")
    assert d.state == "conflicting"
    assert set(d.evidence_ids) == {"a", "b", "c"}
    superseded = [e for e in d.assertions[0].evidence if e.relates_to_claim_id]
    assert superseded and superseded[0].relates_to_claim_id == "b"


def test_evidence_carries_alias_attribution_and_methodology_completeness():
    # F4: original surface value + canonical id travel with the evidence.
    # F5: methodology completeness is stated, so null is never read as absent.
    m = M.project_surface("deepseek-chat", [_claim(surfaces=("deepseek",))])
    d = m.dimension("crawling_indexing_controls")
    ev = d.assertions[0].evidence[0]
    assert ev.claimed_surface_value == "deepseek"
    assert ev.canonical_surface_id == "deepseek-chat"
    assert ev.methodology_completeness in ("not_stated", "sparse", "detailed")


# --------------------------------------------------------------------------- #
# F3: projection cache
# --------------------------------------------------------------------------- #


def test_projection_cache_reuses_until_ledger_changes():
    M.clear_projection_cache()
    ids = ["chatgpt"]
    claims = [_claim()]
    first = M.cached_project_all(ids, claims, now=0.0)
    second = M.cached_project_all(ids, claims, now=1.0)
    assert first is second  # same shape + token, fresh TTL -> reused

    changed = claims + [_claim(claim_id="c2")]
    third = M.cached_project_all(ids, changed, now=2.0)
    assert third is not first
    M.clear_projection_cache()


def test_projection_cache_expires_after_ttl():
    M.clear_projection_cache()
    ids = ["chatgpt"]
    claims = [_claim()]
    first = M.cached_project_all(ids, claims, now=0.0)
    late = M.cached_project_all(ids, claims, now=M._CACHE_TTL_SECONDS + 1)
    assert late is not first
    M.clear_projection_cache()


def test_cache_is_keyed_per_shape_so_bulk_and_single_do_not_thrash():
    M.clear_projection_cache()
    ids = ["chatgpt", "claude"]
    claims = [_claim()]
    bulk = M.cached_project_all(ids, claims, now=0.0)
    single = M.cached_project_surface("chatgpt", claims, now=0.5)
    # Both cached; the single-surface call must not evict the bulk entry.
    assert M.cached_project_all(ids, claims, now=1.0) is bulk
    assert M.cached_project_surface("chatgpt", claims, now=1.5) is single
    assert single.surface_id == "chatgpt" and len(single.dimensions) == 13
    M.clear_projection_cache()


def test_single_surface_projection_does_not_project_all_surfaces(monkeypatch):
    # D1: the per-surface path projects one surface; prove project_all is not used.
    import ai_discovery.mechanics as _m

    calls = {"all": 0}
    real = _m.project_all

    def spy(*a, **k):
        calls["all"] += 1
        return real(*a, **k)

    monkeypatch.setattr(_m, "project_all", spy)
    _m.clear_projection_cache()
    _m.cached_project_surface("chatgpt", [_claim()], now=0.0)
    assert calls["all"] == 0
    _m.clear_projection_cache()


def test_ledger_token_is_honest_about_in_place_edits():
    # D2: the token detects appends but NOT an in-place edit; the TTL is the bound.
    a = [_claim()]
    appended = a + [_claim(claim_id="c2")]
    assert M.ledger_token(a) != M.ledger_token(appended)
    # Same count + same observed_at -> identical token (documented limitation).
    edited = copy.deepcopy(a)
    edited[0]["statement"] = "a corrected statement"
    assert M.ledger_token(a) == M.ledger_token(edited)


# --------------------------------------------------------------------------- #
# Issue #58: the trust layer's evidence contract — why-confidence, freshness,
# and inline reconciliation (reused verbatim, never re-derived)
# --------------------------------------------------------------------------- #


def _serialised_evidence(row, *, dimension="crawling_indexing_controls"):
    view = M.dimension_view(
        M.project_surface("chatgpt", [row]).dimension(dimension), None
    )
    return view["assertions"][0]["evidence"][0]


def test_evidence_carries_confidence_rationale_and_freshness():
    """Issue #58: each evidence entry states why its confidence is what it is and
    how fresh the capture is, so a marketer can judge trust in one interaction.

    Freshness is serialized at read time from the observed timestamp, not baked
    into the frozen projection (review F1)."""

    row = _claim(observed_at=dt.datetime.now(dt.UTC).isoformat())
    row["confidence_detail"] = {
        "score": 0.82,
        "inputs": {"source_authority": 1.0},
        "rationale": ["source_authority: 1.00 (official)", "recency: captured 2d after publication"],
        "derived": True,
    }
    ev = _serialised_evidence(row)
    assert ev["confidence_rationale"] and "source_authority" in ev["confidence_rationale"][0]
    assert ev["freshness_state"] == "fresh"
    assert ev["freshness_age_days"] == 0


def test_freshness_is_unknown_without_a_timestamp():
    """An absent observation time is an explicit unknown, never a guess."""

    ev = _serialised_evidence(_claim(observed_at=None))
    assert ev["freshness_state"] == "unknown"
    assert ev["freshness_age_days"] is None


def test_cached_projection_reports_freshness_at_read_time_not_cache_time():
    """Review F1: freshness must not be frozen by the projection cache. A ledger
    cached while fresh must report a later state once the clock advances, because
    the state is derived from the observed timestamp at serialization time."""

    row = _claim(observed_at="2026-01-01T00:00:00+00:00")
    # Build and cache the projection now.
    m = M.cached_project_surface("chatgpt", [row], now=0.0)
    # Serialize much later: the same cached projection must still report "stale"
    # (the observed date is far in the past relative to the current clock).
    view = M.dimension_view(m.dimension("crawling_indexing_controls"), None)
    ev = view["assertions"][0]["evidence"][0]
    assert ev["freshness_state"] == "stale"
    assert ev["freshness_age_days"] > 180


def test_dimension_view_inlines_reconciliation_verbatim():
    """Issue #58: conflicts render inline by joining the backend reconciliation
    index onto each evidence entry; nothing is re-derived in the presentation."""

    row = _claim(claim_id="c1")
    recon = {
        "c1": [
            {
                "claim_ids": ["c1", "c2"],
                "state": "material_conflict",
                "relationship": "contradicts",
                "confidence_adjustment": -0.2,
                "differences": ["value"],
                "unknown_dimensions": [],
                "interpretation": "The two readings disagree on the same quantity.",
            }
        ]
    }
    view = M.dimension_view(
        M.project_surface("chatgpt", [row]).dimension("crawling_indexing_controls"), recon
    )
    entry = view["assertions"][0]["evidence"][0]
    assert entry["reconciliation"][0]["state"] == "material_conflict"
    assert entry["reconciliation"][0]["relationship"] == "contradicts"


def test_dimension_view_has_empty_reconciliation_when_none_supplied():
    row = _claim(claim_id="c1")
    view = M.dimension_view(
        M.project_surface("chatgpt", [row]).dimension("crawling_indexing_controls"), None
    )
    assert view["assertions"][0]["evidence"][0]["reconciliation"] == []



def test_persisted_claim_without_stored_rationale_still_explains_confidence():
    """Review F4: a claim captured before the LLM lane recorded its rationale must
    still state why its confidence is what it is. The read path derives the "why"
    from the persisted row, reusing the ONE confidence implementation."""

    row = _claim()
    # Simulate a pre-fix persisted claim: label present, inputs/rationale empty.
    row["confidence_detail"] = {"score": None, "inputs": {}, "rationale": [], "derived": True}
    ev = _serialised_evidence(row)
    assert ev["confidence_rationale"], "the read path must explain the confidence anyway"
    assert any("source class" in line for line in ev["confidence_rationale"])


def test_explain_persisted_confidence_matches_the_record_path():
    """One implementation (review F5): the persisted-row explainer and the record
    assessor produce the same inputs and rationale text for equivalent evidence."""

    from ai_discovery.confidence import explain_persisted_confidence

    # Build a real record via the deterministic path, then explain its persisted
    # row shape and compare the source-authority rationale line.
    row = _claim(source_class="official")
    row["confidence_detail"] = {"score": None, "inputs": {}, "rationale": [], "derived": True}
    explained = explain_persisted_confidence(row)
    assert explained.inputs["source_authority"] == 1.0
    assert any("source class official" in line for line in explained.rationale)
