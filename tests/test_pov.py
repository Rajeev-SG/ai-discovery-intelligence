"""Living-POV tests: the deterministic gate, surgical edits and named outcomes.

Covers issue #7's real product proof and the frontier-review fixes:
one real evidence change updates exactly one proposition (before/after +
changelog); a current event correctly produces no POV change; replay is
idempotent regardless of how many events share a topic; significance
discriminates a material change from a repeat/trivial one; contradictory
evidence is retained and caps confidence; and an unknown confidence fails loudly.
"""

from __future__ import annotations

import datetime as dt

import pytest

from ai_discovery.brief import ConfidenceLabel
from ai_discovery.pov import (
    PovPolicy,
    PovProposition,
    PovState,
    apply_event,
    evaluate_event,
    load_policy,
    render_changelog,
    render_pov_body,
    significance_of,
    to_pov_confidence,
)

UTC = dt.UTC


def _state() -> PovState:
    return PovState(
        propositions=[
            PovProposition(
                id="pov-retrieval-systems",
                section="Retrieval",
                base_text="Retrieval stacks differ per surface.",
                topics=["retrieval_index", "citations_sources", "crawler_index_policy"],
            ),
            PovProposition(
                id="pov-channel-prioritisation",
                section="Channels",
                base_text="Prioritise by measured behaviour.",
                topics=["audience_usage", "referrals_conversion"],
            ),
        ]
    )


class _Event:
    def __init__(self, **kw):
        self.id = kw.get("id", "evt1")
        self.title = kw.get("title", "A change")
        self.effective_from = kw.get("effective_from")
        self.published_at = kw.get("published_at")
        self.observed_at = kw.get("observed_at", dt.datetime(2026, 9, 18, tzinfo=UTC))


def _claim(**kw):
    base = {
        "claim_id": "c1",
        "topic": "crawler_index_policy",
        "confidence": "medium",
        "relationship": "new",
        "status": "current",
        "surfaces": ["chatgpt"],
        "value": [{"value_text": "24", "value_number": None}],
        "statement": "OpenAI adjusts search results ~24h after a robots.txt update.",
    }
    base.update(kw)
    return base


# --- the gate --------------------------------------------------------------- #


def test_material_event_adopts_and_is_surgical():
    """One real change updates exactly one proposition; others are byte-identical."""
    state = _state()
    before_other = state.proposition("pov-channel-prioritisation").statement()
    policy = load_policy()

    decision = apply_event(
        state=state,
        event=_Event(id="evt-material"),
        claim=_claim(),
        policy=policy,
    )

    assert decision.adopt is True
    assert decision.proposition_id == "pov-retrieval-systems"
    assert state.proposition("pov-channel-prioritisation").statement() == before_other
    assert state.proposition("pov-retrieval-systems").supporting
    assert len(state.changelog) == 1

    revision = state.changelog[0]
    assert revision.old_statement != revision.new_statement
    assert revision.evidence_ids == ["c1"]
    text = render_changelog(state)
    assert "Before" in text and "After" in text and "c1" in text


def test_topic_a_proposition_does_not_own_makes_no_change():
    state = _state()
    decision = apply_event(
        state=state,
        event=_Event(id="evt-other"),
        claim=_claim(topic="commerce_ads"),
        policy=load_policy(),
    )
    assert decision.adopt is False
    assert "no proposition owns" in decision.reason
    assert state.changelog == []
    for proposition in state.propositions:
        assert proposition.bullets() == []


def test_optimisation_implication_never_changes_the_pov():
    state = _state()
    decision = evaluate_event(
        event=_Event(),
        claim=_claim(topic="optimisation_implication"),
        state=state,
        policy=load_policy(),
    )
    assert decision.adopt is False


def test_low_confidence_event_is_skipped():
    state = _state()
    decision = evaluate_event(
        event=_Event(),
        claim=_claim(confidence="low"),
        state=state,
        policy=PovPolicy(min_confidence=ConfidenceLabel.MEDIUM),
    )
    assert decision.adopt is False
    assert "confidence" in decision.reason


def test_event_with_no_claim_is_skipped():
    state = _state()
    decision = evaluate_event(event=_Event(), claim=None, state=state, policy=load_policy())
    assert decision.adopt is False
    assert "no linked validated claim" in decision.reason


def test_ambiguous_topic_ownership_is_never_adopted_automatically():
    state = PovState(
        propositions=[
            PovProposition(id="a", section="A", base_text="a", topics=["measurement"]),
            PovProposition(id="b", section="B", base_text="b", topics=["measurement"]),
        ]
    )
    decision = evaluate_event(
        event=_Event(), claim=_claim(topic="measurement"), state=state, policy=load_policy()
    )
    assert decision.adopt is False


def test_unknown_confidence_label_fails_loudly():
    with pytest.raises(ValueError):
        to_pov_confidence("probably-fine")


# --- F2: significance must discriminate (not just "topic + has a number") ---- #

_NUMERIC = {
    "topic": "crawler_index_policy",
    "surfaces": ["chatgpt"],
    "value": [{"value_number": 100.0, "value_text": "100"}],
    "status": "current",
}


def test_repeat_of_incumbent_value_is_not_material():
    """Re-reporting the known value is magnitude 0 and cannot clear the gate."""
    claim = dict(_NUMERIC, claim_id="c1", statement="x")
    first = significance_of(claim, prior_value=None)
    repeat = significance_of(claim, prior_value=100.0)
    assert repeat < first
    state = _state()
    # Seed the incumbent bullet with value 100.
    state.proposition("pov-retrieval-systems").supporting.append(
        __import__("ai_discovery.pov", fromlist=["PovEvidenceBullet"]).PovEvidenceBullet(
            slot="crawler_index_policy",
            text="incumbent",
            claim_id="inc",
            event_id="e0",
            confidence=ConfidenceLabel.MEDIUM,
            value_number=100.0,
        )
    )
    decision = evaluate_event(
        event=_Event(id="repeat"),
        claim=dict(_NUMERIC, claim_id="c1", confidence="medium", statement="x"),
        state=state,
        policy=load_policy(),
    )
    assert decision.adopt is False
    assert "no material change" in decision.reason


def test_large_change_is_more_significant_than_small_change():
    small = significance_of(
        dict(_NUMERIC, value=[{"value_number": 102.0}]), prior_value=100.0
    )
    large = significance_of(
        dict(_NUMERIC, value=[{"value_number": 180.0}]), prior_value=100.0
    )
    assert large > small


def test_contested_claim_scores_lower_persistence():
    current = significance_of(dict(_NUMERIC, status="current"), prior_value=None)
    contested = significance_of(dict(_NUMERIC, status="contested"), prior_value=None)
    assert contested < current


# --- F3: supporting vs contradicting evidence ------------------------------- #

def test_contradicting_evidence_is_retained_and_caps_confidence():
    from ai_discovery.pov import PovEvidenceBullet

    state = _state()
    proposition = state.proposition("pov-retrieval-systems")
    proposition.supporting.append(
        PovEvidenceBullet(
            slot="retrieval_index",
            text="strong supporting finding",
            claim_id="sup",
            event_id="e-sup",
            confidence=ConfidenceLabel.HIGH,
        )
    )
    from ai_discovery.pov import ProcessedEvent, watermark_key

    state.processed_events[watermark_key("e-sup", "sup")] = ProcessedEvent(
        event_id="e-sup", claim_id="sup", proposition_id=proposition.id, slot="retrieval_index"
    )
    assert proposition.confidence() == ConfidenceLabel.HIGH

    # A contradicting claim must be retained, not overwrite the supporting one.
    apply_event(
        state=state,
        event=_Event(id="e-con"),
        claim=_claim(claim_id="con", topic="retrieval_index", relationship="contradicts"),
        policy=load_policy(),
    )
    assert proposition.supporting_ids() == ["sup"]
    assert proposition.contradicting_ids() == ["con"]
    assert proposition.confidence() == ConfidenceLabel.LOW
    assert proposition.is_contested
    body = render_pov_body(state)
    assert "Contradicting evidence: con" in body

    # The changelog captures the contradiction, preserving the tension.
    assert state.changelog[-1].evidence_ids == ["con"]


# --- F1: durable idempotency regardless of shared topics -------------------- #

def test_replay_is_idempotent_with_multiple_events_on_one_topic():
    """Two events on the same topic: a full replay adds no bullets or changelog."""
    policy = load_policy()
    state = _state()
    events = [
        (_Event(id="e1"), _claim(claim_id="cA", topic="retrieval_index")),
        (_Event(id="e2"), _claim(claim_id="cB", topic="retrieval_index")),
    ]
    for event, claim in events:
        apply_event(state=state, event=event, claim=claim, policy=policy)

    snapshot = state.model_dump(mode="json")
    changelog_len = len(state.changelog)

    # Replay the whole history (as build_pov.py does on every run).
    for event, claim in events:
        decision = apply_event(state=state, event=event, claim=claim, policy=policy)
        assert decision.adopt is False, "a processed event must not re-adopt"

    assert len(state.changelog) == changelog_len
    assert state.model_dump(mode="json") == snapshot


# --- F4: bullet text prefers the validated claim statement ------------------ #

def test_bullet_uses_claim_statement_over_generic_event_title():
    state = _state()
    apply_event(
        state=state,
        event=_Event(id="e1", title="A crawler policy change"),
        claim=_claim(statement="OpenAI adjusts search results ~24h after a robots.txt update."),
        policy=load_policy(),
    )
    body = render_pov_body(state)
    assert "OpenAI adjusts search results ~24h after a robots.txt update." in body
    assert "A crawler policy change" not in body


# --- rendering -------------------------------------------------------------- #

def test_rendered_body_has_stable_markers_and_sections():
    state = _state()
    apply_event(
        state=state, event=_Event(id="e1"), claim=_claim(), policy=load_policy()
    )
    body = render_pov_body(state)
    assert "### Retrieval" in body
    assert "pov-retrieval-systems" in body
    assert "Supporting evidence:" in body


def test_proposition_confidence_reports_weakest_supporting():
    from ai_discovery.pov import PovEvidenceBullet

    proposition = PovProposition(
        id="p",
        section="S",
        base_text="b",
        topics=["a"],
        supporting=[
            PovEvidenceBullet(slot="a", text="t", claim_id="c1", event_id="e1", confidence=ConfidenceLabel.HIGH),
            PovEvidenceBullet(slot="b", text="t", claim_id="c2", event_id="e2", confidence=ConfidenceLabel.LOW),
        ],
    )
    assert proposition.confidence() == ConfidenceLabel.LOW


# --- review #2 fixes -------------------------------------------------------- #

def test_tiny_relative_change_is_rejected_distinct_from_large():
    """A 24.0 -> 24.1 change is noise; 24 -> 96 is material. The gate must differ."""
    from ai_discovery.pov import _magnitude

    policy = load_policy()
    tiny = dict(_NUMERIC, value=[{"value_number": 24.1}])
    large = dict(_NUMERIC, value=[{"value_number": 96.0}])
    m_tiny, why_tiny = _magnitude(claim=tiny, prior_value=24.0, policy=policy)
    m_large, _ = _magnitude(claim=large, prior_value=24.0, policy=policy)

    assert m_tiny == 0.0, f"tiny delta must be non-material: {why_tiny}"
    assert m_large > policy.min_relative_change
    assert m_large > m_tiny

    # And through the gate: the tiny delta is a skip, the large one adopts.
    state = _state()
    from ai_discovery.pov import PovEvidenceBullet

    state.proposition("pov-retrieval-systems").supporting.append(
        PovEvidenceBullet(
            slot="crawler_index_policy",
            text="incumbent 24",
            claim_id="inc",
            event_id="e0",
            confidence=ConfidenceLabel.MEDIUM,
            value_number=24.0,
        )
    )
    tiny_decision = evaluate_event(
        event=_Event(id="tiny"),
        claim=dict(tiny, claim_id="ct", confidence="medium", statement="x"),
        state=state,
        policy=policy,
    )
    assert tiny_decision.adopt is False
    assert "no material change" in tiny_decision.reason


def test_qualitative_only_claim_is_not_a_measured_change():
    """A policy/qualitative reading has text but is not a measured change."""
    policy = load_policy()
    from ai_discovery.pov import _magnitude

    qualitative = {
        "topic": "crawler_index_policy",
        "value": [{"value_text": "docs were updated", "comparator": "policy_statement"}],
    }
    magnitude, why = _magnitude(claim=qualitative, prior_value=None, policy=policy)
    assert magnitude == policy.magnitude_without_value
    assert "unquantified" in why


def test_one_bullet_per_slot_keeps_the_pov_bounded():
    """Many events on one topic keep exactly one supporting bullet for that slot."""
    state = _state()
    policy = load_policy()
    for index in range(3):
        # Distinct claim ids, distinct values so each is a change.
        apply_event(
            state=state,
            event=_Event(id=f"e{index}"),
            claim=_claim(
                claim_id=f"c{index}",
                topic="crawler_index_policy",
                value=[{"value_number": 100.0 + index}],
            ),
            policy=policy,
        )
    slot_bullets = [
        b for b in state.proposition("pov-retrieval-systems").supporting if b.slot == "crawler_index_policy"
    ]
    assert len(slot_bullets) == 1, "one current position per slot"
    # Rendered statement stays bounded (base + one bullet line).
    statement_lines = state.proposition("pov-retrieval-systems").statement().splitlines()
    assert len(statement_lines) == 2


def test_save_is_atomic_and_locked(tmp_path):
    """save_state writes atomically; update_state serialises read-modify-write."""
    import threading

    from ai_discovery.pov import load_state, save_state, update_state

    path = tmp_path / "state.yaml"
    save_state(_state(), path)
    assert path.exists()
    assert not (tmp_path / "state.yaml.tmp").exists()

    # Concurrent increments must all land (no lost update) thanks to the lock.
    def bump(state):
        state.version += 1

    def worker():
        for _ in range(25):
            update_state(path, bump)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert load_state(path).version == 1 + 100, "all updates must be preserved"
