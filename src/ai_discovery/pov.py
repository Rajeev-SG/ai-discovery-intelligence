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
import fcntl
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

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

# Confidence label vocabulary the POV speaks, strongest -> weakest. Claim
# confidence is validated into this enum on ingest, so an unknown/misparsed
# label fails loudly at the boundary instead of rendering into the document.
_CONFIDENCE_ORDER = [
    ConfidenceLabel.HIGH,
    ConfidenceLabel.MEDIUM_HIGH,
    ConfidenceLabel.MEDIUM,
    ConfidenceLabel.LOW,
    ConfidenceLabel.UNRESOLVED,
]
_CONFIDENCE_RANK = {label: len(_CONFIDENCE_ORDER) - i for i, label in enumerate(_CONFIDENCE_ORDER)}

# Comparators whose "value" is a qualitative reading, not a measured quantity.
# A claim whose only evidence is qualitative is not a measured change and must
# not clear the gate on the strength of "has some text".
_QUALITATIVE_COMPARATORS = {
    "policy_statement",
    "qualitative_finding",
    "qualitative_signal",
    "absence_of_documentation",
}

# Claim `confidence` values (claim_models.Confidence) -> POV label.
_CLAIM_CONFIDENCE = {
    "high": ConfidenceLabel.HIGH,
    "medium": ConfidenceLabel.MEDIUM,
    "low": ConfidenceLabel.LOW,
    "unknown": ConfidenceLabel.UNRESOLVED,
}


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def to_pov_confidence(value: Any) -> ConfidenceLabel:
    """Validate a claim's confidence into the POV label vocabulary.

    An unrecognised label raises rather than defaulting: a misparsed confidence
    must not silently weaken or strengthen a published position.
    """

    if isinstance(value, ConfidenceLabel):
        return value
    key = str(value or "").strip().lower()
    if key in _CLAIM_CONFIDENCE:
        return _CLAIM_CONFIDENCE[key]
    # Accept the POV labels themselves (e.g. "medium_high", "unresolved").
    try:
        return ConfidenceLabel(key)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown confidence label: {value!r}") from exc


class PovPolicy(BaseModel):
    """The deterministic editorial gate (config/pov_policy.yaml)."""

    model_config = ConfigDict(extra="ignore")

    min_significance: float = 3.5
    min_confidence: ConfidenceLabel = ConfidenceLabel.MEDIUM
    require_topic_match: bool = True
    # Magnitude applied to a first-seen quantified claim (the proposition had no
    # prior position for this slot, so adding evidence *is* a change); a repeat of
    # the incumbent value scores magnitude 0 and cannot clear the gate.
    magnitude_with_value: float = 0.8
    magnitude_without_value: float = 0.4
    # A changed value must move at least this relative amount to count as a
    # change; below it the two readings are noise and nothing is adopted.
    min_relative_change: float = 0.10
    # Magnitude is 0.4 at the threshold and rises with the relative change up to
    # 1.0 (a doubling or more).
    magnitude_change_floor: float = 0.4
    # Cap on how much a proposition's confidence may be raised by a single
    # quantified claim with no stated comparison — a number alone is not proof
    # of materiality.
    # topic -> {axis: weight}; unlisted topics fall back to the flat profile.
    significance_topics: dict[str, dict[str, float]] = Field(default_factory=dict)


class PovEvidenceBullet(BaseModel):
    """One evidence bullet: the validated claim statement and its provenance."""

    model_config = ConfigDict(extra="forbid")

    slot: str
    polarity: Literal["supporting", "contradicting"] = "supporting"
    text: str
    claim_id: str
    event_id: str
    confidence: ConfidenceLabel
    # Incumbent value, kept so a later event's magnitude can be measured as a
    # delta against it (a repeat is not a change).
    value_number: float | None = None
    value_text: str | None = None
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
    """A stable POV proposition: id, section, base text, supporting/contradicting evidence."""

    model_config = ConfigDict(extra="forbid")

    id: str
    section: str
    base_text: str
    topics: list[str] = Field(default_factory=list)
    supporting: list[PovEvidenceBullet] = Field(default_factory=list)
    contradicting: list[PovEvidenceBullet] = Field(default_factory=list)
    last_reviewed: dt.datetime | None = None

    def bullets(self) -> list[PovEvidenceBullet]:
        return [*self.supporting, *self.contradicting]

    def bullet_for(self, slot: str) -> PovEvidenceBullet | None:
        return next(
            (b for b in self.bullets() if b.slot == slot and b.polarity == "supporting"), None
        )

    @property
    def is_contested(self) -> bool:
        return bool(self.contradicting)

    def statement(self) -> str:
        """The current rendered text: base position plus one line per evidence item.

        Supporting and contradicting evidence are both rendered, labelled, so a
        contradiction is visible rather than silently overwritten.
        """

        lines = [self.base_text.strip()]
        for bullet in self.supporting:
            lines.append(_bullet_line(bullet))
        for bullet in self.contradicting:
            lines.append(_bullet_line(bullet, contradicting=True))
        return "\n".join(lines)

    def confidence(self) -> ConfidenceLabel:
        """The proposition's confidence, with contradictions capping it.

        Deterministic rule: the proposition is only as strong as its weakest
        supporting item, and if any contradicting evidence exists the position is
        capped at ``low`` and marked contested — a live contradiction cannot be
        hidden behind strong support.
        """

        if not self.supporting:
            base = ConfidenceLabel.UNRESOLVED
        else:
            # Weakest supporting item governs: strong evidence cannot hide a weak one.
            base = min(
                (b.confidence for b in self.supporting),
                key=lambda c: _CONFIDENCE_RANK[c],
            )
        if self.contradicting:
            # A live contradiction caps the position at low (i.e. take the weaker).
            base = min(base, ConfidenceLabel.LOW, key=lambda c: _CONFIDENCE_RANK[c])
        return base

    def evidence_ids(self) -> list[str]:
        return [b.claim_id for b in self.supporting]

    def supporting_ids(self) -> list[str]:
        return [b.claim_id for b in self.supporting]

    def contradicting_ids(self) -> list[str]:
        return [b.claim_id for b in self.contradicting]


def _bullet_line(bullet: PovEvidenceBullet, *, contradicting: bool = False) -> str:
    stamp = bullet.effective_at.date().isoformat() if bullet.effective_at else "undated"
    label = "contradicts" if contradicting else "evidence"
    return f"- {bullet.text} ({label} {bullet.claim_id}; {stamp}; {bullet.confidence.value})"


def watermark_key(event_id: str, claim_id: str) -> str:
    """The durable idempotency key for one (event, claim) pair.

    An event may ground several claims; keying by the pair means every claim on
    an event is processed, and a replay of any pair is skipped.
    """

    return f"{event_id}::{claim_id}"


class ProcessedEvent(BaseModel):
    """A durable record that an event was evaluated and adopted.

    The watermark makes replay idempotent: re-running over the full history
    converges to the same state with zero new changelog entries, regardless of
    how many events share a topic.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str
    claim_id: str
    proposition_id: str
    slot: str
    adopted_at: dt.datetime = Field(default_factory=_utcnow)


class PovState(BaseModel):
    """The whole POV: propositions, the changelog, and the processed watermark."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    propositions: list[PovProposition]
    changelog: list[PovRevision] = Field(default_factory=list)
    # watermark_key(event_id, claim_id) -> ProcessedEvent. Durable idempotency
    # watermark (issue #7 fix).
    processed_events: dict[str, ProcessedEvent] = Field(default_factory=dict)

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
    """Write the state atomically (temp file + rename) under an exclusive lock.

    A reader never sees a half-written file, and two overlapping runs cannot
    interleave: each takes the lock for the whole read-modify-write in
    ``update_state``, so an adoption cannot be silently lost.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        yaml.safe_dump(state.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
    )
    os.replace(tmp, target)


def _lock_path(path: str | Path) -> Path:
    return Path(str(path) + ".lock")


@contextmanager
def _state_lock(path: str | Path) -> Iterator[None]:
    """An exclusive advisory lock around a state read-modify-write."""

    lock = _lock_path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def update_state(path: str | Path, apply: Callable[[PovState], Any]) -> PovState:
    """Lock, load, mutate, atomically save, and return the state.

    ``apply`` receives the loaded state and may mutate it in place; its return
    value is discarded. This is the only supported read-modify-write path, so the
    lock cannot be forgotten by a caller.
    """

    with _state_lock(path):
        state = load_state(path)
        apply(state)
        save_state(state, path)
        return state


def _incumbent_number(proposition: PovProposition | None, slot: str) -> float | None:
    if proposition is None:
        return None
    bullet = proposition.bullet_for(slot)
    return bullet.value_number if bullet else None


def _magnitude(
    *,
    claim: dict[str, Any],
    prior_value: float | None,
    policy: PovPolicy,
) -> tuple[float, str]:
    """Event-specific magnitude: a repeat of the incumbent value is not a change.

    Returns ``(magnitude, explanation)``. When the claim states a number and an
    incumbent number is known, magnitude is the relative change — zero when the
    value is unchanged, so a re-report of a known figure cannot clear the gate.
    With no incumbent number, a quantified claim gets the first-seen magnitude and
    an unquantified one the lower value.
    """

    metrics = claim.get("value") or claim.get("metrics") or []
    number = None
    for metric in metrics:
        if metric.get("value_number") is not None:
            number = float(metric["value_number"])
            break
    # A "measured value" means a number, or a value_text on a metric whose
    # comparator is not one of the qualitative ones. A policy statement or
    # qualitative finding carries text but is not a measured change.
    has_value = any(
        (m.get("value_number") is not None)
        or (
            bool(m.get("value_text"))
            and (m.get("comparator") or "exact") not in _QUALITATIVE_COMPARATORS
        )
        for m in metrics
    )

    if number is not None and prior_value is not None:
        denom = max(abs(prior_value), 1e-9)
        relative = abs(number - prior_value) / denom
        if relative < policy.min_relative_change:
            # A change smaller than the stated threshold is treated as noise:
            # magnitude 0 means the gate rejects it, so a trivial numeric delta
            # cannot adopt a position.
            return (
                0.0,
                (
                    f"relative change {relative:.4f} below threshold "
                    f"{policy.min_relative_change:.2f} (not a material change)"
                ),
            )
        # Map [threshold, 2x threshold..] to [floor, 1.0].
        span = max(1.0 - policy.magnitude_change_floor, 1e-9)
        scaled = policy.magnitude_change_floor + span * min(
            1.0, (relative - policy.min_relative_change) / max(relative, 1e-9)
        )
        return min(1.0, scaled), f"relative change {relative:.2f} vs incumbent"
    if has_value:
        return policy.magnitude_with_value, "first-seen quantified claim"
    return policy.magnitude_without_value, "unquantified claim"


def significance_inputs(
    claim: dict[str, Any],
    policy: PovPolicy | None = None,
    *,
    prior_value: float | None = None,
) -> dict[str, float]:
    """Deterministic significance inputs for a claim (no model, fully stated).

    Editorial constants (reach, commercial_intent, actionability) come from the
    per-topic profile; the *event-specific* axes — magnitude (delta vs the
    incumbent value), breadth (distinct surfaces the claim touches) and
    persistence (contested claims do not persist) — are derived from this claim,
    so the gate discriminates a material change from a trivial re-statement.
    """

    policy = policy or load_policy()
    topic = claim.get("topic") or ""
    profile = dict(_DEFAULT_SIGNIFICANCE)
    profile.update(policy.significance_topics.get(topic, {}))

    magnitude, _ = _magnitude(claim=claim, prior_value=prior_value, policy=policy)
    surfaces = claim.get("surfaces") or []
    status = claim.get("status") or "current"
    profile["magnitude"] = magnitude
    profile["breadth"] = min(1.0, 0.4 + 0.2 * len(surfaces))
    profile["persistence"] = 0.2 if status == "contested" else 0.6
    return profile


def significance_of(
    claim: dict[str, Any],
    scorer: SignificanceScorer | None = None,
    policy: PovPolicy | None = None,
    *,
    prior_value: float | None = None,
) -> float:
    return (scorer or SignificanceScorer.from_config()).score(
        **significance_inputs(claim, policy, prior_value=prior_value)
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

    confidence = to_pov_confidence((claim or {}).get("confidence")).value if claim else "unresolved"

    if claim is None:
        return PovDecision(
            adopt=False,
            reason="event has no linked validated claim",
            significance=0.0,
            confidence=confidence,
        )

    topic = claim.get("topic") or ""
    proposition = state.proposition_for_topic(topic) if policy.require_topic_match else None
    if proposition is None:
        return PovDecision(
            adopt=False,
            reason=f"no proposition owns topic {topic!r}",
            significance=0.0,
            confidence=confidence,
        )

    # Magnitude uses the incumbent value for the claim's own slot when known, and
    # the corroboration baseline is the proposition's current supporting evidence.
    slot = claim.get("topic") or ""
    prior_value = _incumbent_number(state.proposition_for_topic(slot), slot)
    magnitude, magnitude_note = _magnitude(claim=claim, prior_value=prior_value, policy=policy)
    inputs = significance_inputs(
        claim, policy, prior_value=prior_value
    )
    significance = (SignificanceScorer.from_config()).score(**inputs)

    label = to_pov_confidence(claim.get("confidence"))
    if _CONFIDENCE_RANK[label] < _CONFIDENCE_RANK[policy.min_confidence]:
        return PovDecision(
            adopt=False,
            reason=f"claim confidence {label.value!r} below {policy.min_confidence.value!r}",
            significance=significance,
            confidence=label.value,
        )

    if magnitude <= 0.0:
        return PovDecision(
            adopt=False,
            reason=f"no material change ({magnitude_note})",
            significance=significance,
            confidence=label.value,
        )

    if significance < policy.min_significance:
        return PovDecision(
            adopt=False,
            reason=(
                f"event significance {significance:.2f} below {policy.min_significance:.2f} "
                f"({magnitude_note}; breadth {inputs['breadth']:.2f})"
            ),
            significance=significance,
            confidence=label.value,
        )

    return PovDecision(
        adopt=True,
        proposition_id=proposition.id,
        reason=(
            f"material {topic} change: significance {significance:.2f} >= "
            f"{policy.min_significance:.2f}, confidence {label.value} ({magnitude_note})"
        ),
        significance=significance,
        confidence=label.value,
    )


def _first_value(claim: dict[str, Any]) -> tuple[float | None, str | None]:
    for metric in claim.get("value") or claim.get("metrics") or []:
        if metric.get("value_number") is not None:
            return float(metric["value_number"]), metric.get("value_text")
        if metric.get("value_text"):
            return None, metric["value_text"]
    return None, None


def apply_decision(
    *,
    state: PovState,
    decision: PovDecision,
    event: Any,
    claim: dict[str, Any],
    now: dt.datetime | None = None,
) -> PovRevision | None:
    """Apply one adopting decision: add the bullet and log the change.

    The edit is surgical: only one proposition changes, and the before/after
    statements are captured for the changelog. Supporting and contradicting
    evidence are kept in separate lists; a claim never evicts an unrelated one.
    """

    if not decision.adopt or decision.proposition_id is None:
        return None
    proposition = state.proposition(decision.proposition_id)
    if proposition is None:  # pragma: no cover - decision guarantees existence
        return None

    stamp = now or _utcnow()
    topic = claim.get("topic") or ""
    old_statement = proposition.statement()

    # Prefer the validated claim statement; the event title is ingest metadata and
    # is only a fallback when the claim carries no statement.
    text = (claim.get("statement") or getattr(event, "title", None) or "").strip()
    effective = (
        getattr(event, "effective_from", None)
        or getattr(event, "published_at", None)
        or getattr(event, "observed_at", None)
    )
    value_number, value_text = _first_value(claim)
    claim_id = claim.get("claim_id") or ""
    relationship = (claim.get("relationship") or "new").lower()
    polarity = "contradicting" if relationship == "contradicts" else "supporting"
    bullet = PovEvidenceBullet(
        slot=topic,
        polarity=polarity,
        text=text,
        claim_id=claim_id,
        event_id=getattr(event, "id", "") or "",
        confidence=to_pov_confidence(claim.get("confidence")),
        value_number=value_number,
        value_text=value_text,
        effective_at=effective,
        added_at=stamp,
    )

    # One current position per slot: a new claim for a slot replaces that slot's
    # existing bullet (deterministic — the newest effective reading wins), so the
    # rendered POV stays bounded. Other slots and the opposite polarity are kept:
    # a supporting claim never evicts contradicting evidence, and vice versa.
    if polarity == "contradicting":
        proposition.contradicting = [
            b for b in proposition.contradicting if b.slot != topic and b.claim_id != claim_id
        ]
        proposition.contradicting.append(bullet)
    else:
        proposition.supporting = [
            b for b in proposition.supporting if b.slot != topic and b.claim_id != claim_id
        ]
        proposition.supporting.append(bullet)
    proposition.last_reviewed = stamp

    revision = PovRevision(
        proposition_id=proposition.id,
        changed_at=stamp,
        reason=decision.reason,
        event_id=getattr(event, "id", "") or "",
        evidence_ids=[claim_id] if claim_id else [],
        old_statement=old_statement,
        new_statement=proposition.statement(),
        significance=decision.significance,
        confidence=decision.confidence,
    )
    state.changelog.append(revision)
    state.processed_events[watermark_key(revision.event_id, claim_id)] = ProcessedEvent(
        event_id=revision.event_id,
        claim_id=claim_id,
        proposition_id=proposition.id,
        slot=topic,
        adopted_at=stamp,
    )
    return revision


def apply_event(
    *,
    state: PovState,
    event: Any,
    claim: dict[str, Any] | None,
    policy: PovPolicy,
    now: dt.datetime | None = None,
) -> PovDecision:
    """Gate + apply one event. Returns the decision (adopted or skipped).

    Idempotent: an event already in the processed watermark is skipped, so
    replaying the full history converges to the same state with no new changelog
    entries.
    """

    event_id = getattr(event, "id", "") or ""
    claim_id = (claim or {}).get("claim_id") or ""
    if event_id and watermark_key(event_id, claim_id) in state.processed_events:
        return PovDecision(
            adopt=False,
            reason=f"event/claim {event_id!r}/{claim_id!r} already processed",
            significance=0.0,
            confidence="unresolved",
        )
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
        meta = f"**{proposition.id}** · confidence: {proposition.confidence().value}"
        if proposition.is_contested:
            meta += " · **contested**"
        if proposition.last_reviewed is not None:
            meta += f" · last reviewed: {proposition.last_reviewed.date().isoformat()}"
        lines.append(meta)
        lines.append("")
        lines.extend(proposition.statement().splitlines())
        if proposition.supporting_ids():
            lines.append("")
            lines.append("Supporting evidence: " + ", ".join(proposition.supporting_ids()))
        if proposition.contradicting_ids():
            lines.append("")
            lines.append("Contradicting evidence: " + ", ".join(proposition.contradicting_ids()))
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
