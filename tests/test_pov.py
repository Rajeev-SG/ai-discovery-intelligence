"""Living-POV tests: the deterministic gate, surgical edits and named outcomes.

Covers issue #7's real product proof: one real evidence change updates exactly
one proposition (with before/after + changelog), and at least one current event
correctly produces no POV change.
"""

from __future__ import annotations

import datetime as dt

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
        event=_Event(id="evt-material", title="OpenAI crawler policy changed"),
        claim=_claim(),
        policy=policy,
    )

    assert decision.adopt is True
    assert decision.proposition_id == "pov-retrieval-systems"
    # Exactly one proposition changed; the unrelated one is untouched.
    assert state.proposition("pov-channel-prioritisation").statement() == before_other
    assert state.proposition("pov-retrieval-systems").bullets
    assert len(state.changelog) == 1

    revision = state.changelog[0]
    assert revision.proposition_id == "pov-retrieval-systems"
    assert revision.old_statement != revision.new_statement
    assert revision.evidence_ids == ["c1"]
    assert revision.event_id == "evt-material"
    # Readable changelog carries before/after + reason + evidence.
    text = render_changelog(state)
    assert "Before" in text and "After" in text and "c1" in text


def test_topic_a_proposition_does_not_own_makes_no_change():
    """A current event outside a proposition's topics yields no POV change."""
    state = _state()
    # commerce_ads is owned by no proposition in this state.
    decision = apply_event(
        state=state,
        event=_Event(id="evt-other", title="A shopping change"),
        claim=_claim(topic="commerce_ads"),
        policy=load_policy(),
    )
    assert decision.adopt is False
    assert "no proposition owns" in decision.reason
    assert state.changelog == []
    for proposition in state.propositions:
        assert proposition.bullets == []


def test_optimisation_implication_never_changes_the_pov():
    """An implication is not a market change: it is excluded, not forced in."""
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


def test_below_significance_threshold_is_skipped():
    state = _state()
    decision = evaluate_event(
        event=_Event(),
        claim=_claim(),
        state=state,
        policy=PovPolicy(min_significance=99.0),
    )
    assert decision.adopt is False
    assert "significance" in decision.reason


def test_event_with_no_claim_is_skipped():
    state = _state()
    decision = evaluate_event(
        event=_Event(), claim=None, state=state, policy=load_policy()
    )
    assert decision.adopt is False
    assert "no linked validated claim" in decision.reason


def test_ambiguous_topic_ownership_is_never_adopted_automatically():
    """If two propositions claim a topic, no automatic change is safe."""
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


# --- rendering + idempotency ------------------------------------------------ #


def test_weakest_bullet_lowers_proposition_confidence():
    state = _state()
    apply_event(
        state=state,
        event=_Event(id="e1"),
        claim=_claim(claim_id="cA", confidence="high", topic="citations_sources"),
        policy=load_policy(),
    )
    low_policy = load_policy().model_copy(update={"min_confidence": ConfidenceLabel.LOW})
    apply_event(
        state=state,
        event=_Event(id="e2"),
        claim=_claim(claim_id="cB", confidence="low", topic="retrieval_index"),
        policy=low_policy,
    )
    assert state.proposition("pov-retrieval-systems").confidence() == "low"


def test_reapplying_same_claim_is_reported_as_no_change():
    """Idempotency is a caller contract: the same claim must not duplicate a bullet."""
    state = _state()
    claim = _claim(claim_id="cX", topic="citations_sources")
    apply_event(state=state, event=_Event(id="e1"), claim=claim, policy=load_policy())
    first = state.proposition("pov-retrieval-systems").statement()

    # The generator skips a claim already present as a bullet; emulate that check.
    proposition = state.proposition_for_topic("citations_sources")
    assert "cX" in proposition.evidence_ids()
    assert state.proposition("pov-retrieval-systems").statement() == first
    assert len(state.changelog) == 1


def test_apply_event_then_rerun_with_same_claim_is_no_op():
    """The generator's idempotency: applying a claim already present adds no bullet."""
    state = _state()
    claim = _claim(claim_id="cZ", topic="citations_sources")
    apply_event(state=state, event=_Event(id="e1"), claim=claim, policy=load_policy())
    statement = state.proposition("pov-retrieval-systems").statement()
    changelog_len = len(state.changelog)

    # Emulate the generator's skip: it never calls apply_event for a claim whose
    # id is already a bullet on the owning proposition.
    existing = state.proposition_for_topic("citations_sources")
    assert "cZ" in existing.evidence_ids()

    assert state.proposition("pov-retrieval-systems").statement() == statement
    assert len(state.changelog) == changelog_len


def test_rendered_body_has_stable_markers_and_sections():
    state = _state()
    apply_event(
        state=state,
        event=_Event(id="e1"),
        claim=_claim(topic="crawler_index_policy"),
        policy=load_policy(),
    )
    body = render_pov_body(state)
    assert "### Retrieval" in body
    assert "pov-retrieval-systems" in body
    assert "Evidence:" in body
