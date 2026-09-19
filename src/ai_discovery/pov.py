"""Living POV: deterministic, evidence-gated editorial propositions (issue #7).

The executive POV is product data, not a weekly essay. Each proposition has a
stable id, a stable editorial base text, and one *evidence bullet* per claim
topic it owns. A change event may propose a revision to a proposition; adoption
is gated by deterministic editorial rules (no model decides):

* the event's claim topic must be owned by exactly one proposition;
* the claim's evidence-derived confidence must clear ``min_confidence``;
* the event's derived significance must clear ``min_significance``.

When an event qualifies, only the proposition's bullet for that topic is
replaced, so the rendered POV diff is surgical — unrelated sections are
byte-identical. Every adoption writes a changelog entry with the old and new
statement, the reason, and the evidence ids. "No POV change" is a first-class
outcome: an event that fails any gate leaves the POV untouched.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .brief import ConfidenceLabel, SignificanceScorer

POV_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "pov_policy.yaml"

_CONFIDENCE_RANK = {
    ConfidenceLabel.HIGH: 4,
    ConfidenceLabel.MEDIUM_HIGH: 3,
    ConfidenceLabel.MEDIUM: 2,
    ConfidenceLabel.LOW: 1,
    ConfidenceLabel.UNRESOLVED: 0,
}

# Every significance axis the gate uses is a stated editorial default in
# config/pov_policy.yaml (`significance_topics`). An unlisted topic defaults to
# this flat, below-gate profile, so an unknown topic cannot move the POV.
_DEFAULT_SIGNIFICANCE: dict[str, float] = {
    "reach": 0.5,
    "commercial_intent": 0.5,
    "magnitude": 0.5,
    "breadth": 0.5,
    "persistence": 0.5,
    "actionability": 0.5,
}


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class PovPolicy(BaseModel):
    """The deterministic editorial gate (config/pov_policy.yaml)."""

    model_config = ConfigDict(extra="ignore")

    min_significance: float = 3.5
    min_confidence: ConfidenceLabel = ConfidenceLabel.MEDIUM
    require_topic_match: bool = True
    max_propositions_per_event: int = 1
    magnitude_with_value: float = 0.8
    magnitude_without_value: float = 0.4
    # topic -> {axis: weight}; unlisted topics fall back to the flat profile.
    significance_topics: dict[str, dict[str, float]] = Field(default_factory=dict)


class PovEvidenceBullet(BaseModel):
    """One confirmed evidence bullet, keyed by the claim topic that owns it."""

    model_config = ConfigDict(extra="forbid")

    slot: str
    text: str
    claim_id: str
    event_id: str
    confidence: str
    effective_at: dt.datetime | None = None
    added_at: dt.datetime = Field(default_factory=_utcnow)


class PovRevision(BaseModel):
    """One changelog entry: a surgical change to exactly one proposition."""

    model_config = ConfigDict(extra="forbid")

    proposition_id: str
    changed_at: dt.datetime = Field(default_factory=_utcnow)
    reason: str
    event_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    old_statement: str
    new_statement: str
    significance: float
    confidence: str


class PovProposition(BaseModel):
    """A stable POV proposition: id, section, baseline text, evidence bullets."""

    model_config = ConfigDict(extra="forbid")

    id: str
    section: str
    base_text: str
    topics: list[str] = Field(default_factory=list)
    bullets: list[PovEvidenceBullet] = Field(default_factory=list)
    last_reviewed: dt.datetime | None = None

    def bullet_for(self, slot: str) -> PovEvidenceBullet | None:
        return next((b for b in self.bullets if b.slot == slot), None)

    def statement(self) -> str:
        """The current rendered text: base position plus one line per bullet."""

        lines = [self.base_text.strip()]
        for bullet in self.bullets:
            stamp = bullet.effective_at.date().isoformat() if bullet.effective_at else "undated"
            lines.append(
                f"- {bullet.text} (evidence {bullet.claim_id}; {stamp}; {bullet.confidence})"
            )
        return "\n".join(lines)

    def confidence(self) -> str:
        """The proposition's confidence: the weakest bullet cannot be hidden.

        A proposition is only as strong as its weakest confirmed evidence, so a
        weak bullet lowers the whole statement rather than sitting alongside it.
        """

        if not self.bullets:
            return ConfidenceLabel.UNRESOLVED.value
        # Strongest -> weakest. The preposition must report the WEAKEST bullet,
        # so a weak confirmed evidence item cannot hide behind a strong one.
        order = ["high", "medium_high", "medium", "low", "unresolved"]
        labels = {b.confidence for b in self.bullets}
        return max(labels, key=lambda c: order.index(c) if c in order else 99)

    def evidence_ids(self) -> list[str]:
        return [b.claim_id for b in self.bullets]


class PovState(BaseModel):
    """The whole POV: propositions plus the append-only changelog."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    propositions: list[PovProposition]
    changelog: list[PovRevision] = Field(default_factory=list)

    def proposition(self, proposition_id: str) -> PovProposition | None:
        return next((p for p in self.propositions if p.id == proposition_id), None)

    def proposition_for_topic(self, topic: str) -> PovProposition | None:
        matches = [p for p in self.propositions if topic in p.topics]
        # Ambiguity is a configuration error, not a cue to guess: if two
        # propositions claim a topic, no automatic change is safe for it.
        return matches[0] if len(matches) == 1 else None


def load_policy(path: str | Path | None = None) -> PovPolicy:
    raw = yaml.safe_load(Path(path or POV_POLICY_PATH).read_text())
    return PovPolicy(**(raw.get("pov") or {}))


def load_state(path: str | Path) -> PovState:
    return PovState(**yaml.safe_load(Path(path).read_text()))


def save_state(state: PovState, path: str | Path) -> None:
    Path(path).write_text(
        yaml.safe_dump(state.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    )


def significance_inputs(
    claim: dict[str, Any], policy: PovPolicy | None = None
) -> dict[str, float]:
    """Deterministic significance inputs for a claim (no model, fully stated).

    The per-topic axis weights are the editorial profile in
    ``config/pov_policy.yaml``; the only claim-derived input is ``magnitude``,
    which is bumped when the claim carries a stated number.
    """

    policy = policy or load_policy()
    topic = claim.get("topic") or ""
    profile = dict(_DEFAULT_SIGNIFICANCE)
    profile.update(policy.significance_topics.get(topic, {}))

    metrics = claim.get("value") or claim.get("metrics") or []
    has_number = any(
        (m.get("value_number") is not None) or bool(m.get("value_text")) for m in metrics
    )
    profile["magnitude"] = (
        policy.magnitude_with_value if has_number else policy.magnitude_without_value
    )
    return profile


def significance_of(
    claim: dict[str, Any],
    scorer: SignificanceScorer | None = None,
    policy: PovPolicy | None = None,
) -> float:
    return (scorer or SignificanceScorer.from_config()).score(
        **significance_inputs(claim, policy)
    )


class PovDecision(BaseModel):
    """The gate's verdict for one event: adopt (and where) or an explicit skip."""

    model_config = ConfigDict(extra="forbid")

    adopt: bool
    proposition_id: str | None = None
    reason: str
    significance: float
    confidence: str


def evaluate_event(
    *,
    event: Any,
    claim: dict[str, Any] | None,
    state: PovState,
    policy: PovPolicy,
) -> PovDecision:
    """Decide whether one event revises the POV, and which proposition it hits."""

    significance = significance_of(claim, policy=policy) if claim else 0.0
    confidence = (claim or {}).get("confidence") or ConfidenceLabel.UNRESOLVED.value

    if claim is None:
        return PovDecision(
            adopt=False,
            reason="event has no linked validated claim",
            significance=significance,
            confidence=confidence,
        )

    topic = claim.get("topic") or ""
    proposition = state.proposition_for_topic(topic) if policy.require_topic_match else None
    if proposition is None:
        return PovDecision(
            adopt=False,
            reason=f"no proposition owns topic {topic!r}",
            significance=significance,
            confidence=confidence,
        )

    rank = _CONFIDENCE_RANK.get(ConfidenceLabel(confidence), 0)
    if rank < _CONFIDENCE_RANK[policy.min_confidence]:
        return PovDecision(
            adopt=False,
            reason=(
                f"claim confidence {confidence!r} below {policy.min_confidence.value!r}"
            ),
            significance=significance,
            confidence=confidence,
        )

    if significance < policy.min_significance:
        return PovDecision(
            adopt=False,
            reason=(
                f"event significance {significance:.2f} below "
                f"{policy.min_significance:.2f}"
            ),
            significance=significance,
            confidence=confidence,
        )

    return PovDecision(
        adopt=True,
        proposition_id=proposition.id,
        reason=(
            f"material {topic} change: significance {significance:.2f} >= "
            f"{policy.min_significance:.2f}, confidence {confidence}"
        ),
        significance=significance,
        confidence=confidence,
    )


def apply_decision(
    *,
    state: PovState,
    decision: PovDecision,
    event: Any,
    claim: dict[str, Any],
    now: dt.datetime | None = None,
) -> PovRevision | None:
    """Apply one adopting decision: replace the topic's bullet and log the change.

    Returns the changelog entry, or ``None`` when the decision is a skip. The
    edit is surgical: only the bullet for this claim's topic changes, and the
    before/after statements are captured for the changelog.
    """

    if not decision.adopt or decision.proposition_id is None:
        return None
    proposition = state.proposition(decision.proposition_id)
    if proposition is None:  # pragma: no cover - decision guarantees existence
        return None

    stamp = now or _utcnow()
    topic = claim.get("topic") or ""
    old_statement = proposition.statement()

    text = (getattr(event, "title", None) or claim.get("statement") or "").strip()
    effective = (
        getattr(event, "effective_from", None)
        or getattr(event, "published_at", None)
        or getattr(event, "observed_at", None)
    )
    bullet = PovEvidenceBullet(
        slot=topic,
        text=text,
        claim_id=claim.get("claim_id") or "",
        event_id=getattr(event, "id", "") or "",
        confidence=decision.confidence,
        effective_at=effective,
        added_at=stamp,
    )
    proposition.bullets = [b for b in proposition.bullets if b.slot != topic] + [bullet]
    proposition.last_reviewed = stamp

    revision = PovRevision(
        proposition_id=proposition.id,
        changed_at=stamp,
        reason=decision.reason,
        event_id=getattr(event, "id", "") or "",
        evidence_ids=[bullet.claim_id] if bullet.claim_id else [],
        old_statement=old_statement,
        new_statement=proposition.statement(),
        significance=decision.significance,
        confidence=decision.confidence,
    )
    state.changelog.append(revision)
    return revision


def apply_event(
    *,
    state: PovState,
    event: Any,
    claim: dict[str, Any] | None,
    policy: PovPolicy,
    now: dt.datetime | None = None,
) -> PovDecision:
    """Gate + apply one event. Returns the decision (adopted or skipped)."""

    decision = evaluate_event(event=event, claim=claim, state=state, policy=policy)
    if decision.adopt and claim is not None:
        apply_decision(state=state, decision=decision, event=event, claim=claim, now=now)
    return decision


# --- rendering -------------------------------------------------------------- #

GENERATED_START = "<!-- pov:generated:start -->"
GENERATED_END = "<!-- pov:generated:end -->"


def render_pov_body(state: PovState) -> str:
    """The generated POV block: one section per proposition, stable and surgical."""

    lines: list[str] = []
    for proposition in state.propositions:
        lines.append(f"### {proposition.section}")
        lines.append("")
        meta = f"**{proposition.id}** · confidence: {proposition.confidence()}"
        if proposition.last_reviewed is not None:
            meta += f" · last reviewed: {proposition.last_reviewed.date().isoformat()}"
        lines.append(meta)
        lines.append("")
        lines.extend(proposition.statement().splitlines())
        if proposition.evidence_ids():
            lines.append("")
            lines.append("Evidence: " + ", ".join(proposition.evidence_ids()))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_pov_document(state: PovState, preamble: str) -> str:
    """The full docs/EXECUTIVE_POV.md: static preamble + the generated block.

    Only the block between the markers is regenerated, so unrelated editorial
    text is never rewritten.
    """

    return f"{preamble.rstrip()}\n\n{GENERATED_START}\n{render_pov_body(state)}{GENERATED_END}\n"


def render_changelog(state: PovState) -> str:
    """A readable changelog: old statement, new statement, reason, evidence ids."""

    lines = ["# POV changelog", ""]
    if not state.changelog:
        lines.append("No POV change has been adopted yet.")
        return "\n".join(lines) + "\n"
    for revision in state.changelog:
        lines.append(f"## {revision.changed_at.date().isoformat()} — {revision.proposition_id}")
        lines.append("")
        lines.append(f"- **Reason:** {revision.reason}")
        lines.append(f"- **Event:** `{revision.event_id}`")
        lines.append(
            "- **Evidence:** " + (", ".join(f"`{e}`" for e in revision.evidence_ids) or "none")
        )
        lines.append(
            f"- **Significance:** {revision.significance:.2f} · **Confidence:** {revision.confidence}"
        )
        lines.append("")
        lines.append("**Before**")
        lines.append("")
        lines.append("```")
        lines.append(revision.old_statement)
        lines.append("```")
        lines.append("")
        lines.append("**After**")
        lines.append("")
        lines.append("```")
        lines.append(revision.new_statement)
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
