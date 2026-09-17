"""Compare study contexts before interpreting a numerical disagreement.

Test coverage: tests/test_reconciliation.py (30 tests).
Merge base: main; see PR #11 for the issue-#4 product proof plan.

This module returns a separate agency interpretation. Source claims are immutable;
it never replaces a measured value or treats an unknown context as a match.
"""

from datetime import date
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Note: "supersedes" is intentionally absent — no code path currently produces it.
# A future supersession path (later re-measurement of the same quantity) should
# re-add it to this Literal and implement the branch.
Relationship = Literal["supports", "updates", "contradicts", "supersedes", "contextualises"]


def _norm(value: str | None) -> str | None:
    """Normalise free-text context fields for comparison (case, whitespace)."""
    if value is None:
        return None
    return " ".join(value.strip().lower().split())


ConflictState = Literal[
    "compatible_support",
    "directional_support",
    "methodologically_incomparable",
    "temporal_update",
    "material_conflict",
    "possible_transient_change",
    "unresolved",
]


class StudyClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    surface: str = Field(min_length=1)
    subject: str = Field(
        min_length=1
    )  # E.g. reddit.com; two different cited domains aren't a conflict.
    statement: str
    metric: str | None = None
    denominator: str | None = None
    geography: str | None = None
    mode: str | None = None
    sampling_frame: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    value: float | None = None
    unit: str | None = None
    provisional: bool = False

    @field_validator(
        "metric", "denominator", "geography", "mode", "sampling_frame", "unit", mode="before"
    )
    @classmethod
    def missing_context(cls, value):
        if isinstance(value, str) and value.strip().lower() in {"", "unknown", "undocumented"}:
            return None
        return value

    @model_validator(mode="after")
    def valid_measurement(self):
        if self.value is not None and not isfinite(self.value):
            raise ValueError("Measurement must be finite")
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("Study period ends before it starts")
        return self


class Reconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)
    claim_ids: tuple[str, str]  # (subject, object): first claim updates/supports the second.
    evidence_ids: tuple[str, ...]
    relationship: Relationship
    state: ConflictState
    differences: tuple[str, ...]
    unknown_dimensions: tuple[str, ...]
    interpretation: str
    confidence_adjustment: float  # Applied to agency interpretation, not source claims.


def compare_claims(first: StudyClaim, second: StudyClaim) -> Reconciliation:
    """Conservative comparisons: no inferred mode, denominator or sampling frame.

    Values are exact normalized values. A difference flags a candidate conflict;
    it does not assert statistical significance without uncertainty estimates.
    Non-overlapping periods qualify earlier observations, never erase them.
    """
    if first.id == second.id:
        raise ValueError("Reconciliation requires two distinct claims")
    context = (
        "surface",
        "subject",
        "metric",
        "denominator",
        "geography",
        "mode",
        "sampling_frame",
        "unit",
    )
    differences = tuple(
        key
        for key in context
        if getattr(first, key) is not None
        and getattr(second, key) is not None
        and getattr(first, key) != getattr(second, key)
    )
    unknown = tuple(
        key
        for key in (*context, "period_start", "period_end", "value")
        if getattr(first, key) is None or getattr(second, key) is None
    )
    common = {
        "claim_ids": (first.id, second.id),
        "evidence_ids": tuple(dict.fromkeys((*first.evidence_ids, *second.evidence_ids))),
        "differences": differences,
        "unknown_dimensions": unknown,
    }
    if differences:
        return Reconciliation(
            **common,
            relationship="contextualises",
            state="methodologically_incomparable",
            interpretation=(
                f"These findings differ in {', '.join(differences)} and cannot be reconciled "
                "as estimates of the same quantity. Preserve both findings in their stated "
                "contexts; neither establishes a universal change or absence of change."
                + (
                    " At least one publisher marks its finding provisional."
                    if first.provisional or second.provisional
                    else ""
                )
            ),
            confidence_adjustment=-0.15,
        )
    if unknown:
        return Reconciliation(
            **common,
            relationship="contextualises",
            state="unresolved",
            interpretation=f"Insufficient context to compare: {', '.join(unknown)}. "
            "Missing methodology is not evidence of agreement or contradiction."
            + (
                f" Note: known values disagree ({round(first.value, 2)} vs "
                f"{round(second.value, 2)}"
                + (f" {first.unit}" if first.unit == second.unit and first.unit else "")
                + "); may indicate a genuine conflict once contexts are completed."
                if first.value is not None
                and second.value is not None
                and abs(first.value - second.value) > 1e-6
                and abs(first.value - second.value)
                / max(abs(first.value), abs(second.value), 1e-12)
                > 0.01
                else ""
            ),
            confidence_adjustment=-0.15,
        )
    # All dates and values are known after the conservative missing-data branch.
    assert first.period_start and first.period_end and second.period_start and second.period_end

    # Supersession: a later, non-overlapping, same-context, same-denominator
    # re-measurement with a materially different value supersedes the earlier
    # claim's interpretation. Requires the second period to start AFTER the
    # first period ends (true temporal supersession, not concurrent observation).
    if (
        _norm(first.metric) == _norm(second.metric)
        and _norm(first.geography) == _norm(second.geography)
        and _norm(first.mode) == _norm(second.mode)
        and _norm(first.sampling_frame) == _norm(second.sampling_frame)
        and _norm(first.denominator) == _norm(second.denominator)
        and second.period_start > first.period_end
    ):
        abs_diff = abs(first.value - second.value)
        scale = max(abs(first.value), abs(second.value), 1e-12)
        if abs_diff / scale > 0.01:
            return Reconciliation(
                state="temporal_update",
                relationship="supersedes",
                confidence_adjustment=0.10,
                interpretation=(
                    f"Claim {second.id} supersedes {first.id}: a later re-measurement of "
                    "the same quantity in the same context reports a materially different "
                    "value. Both claims are retained for audit; the later figure is current."
                ),
                **common,
            )

    if first.period_end < second.period_start or second.period_end < first.period_start:
        newer = second if first.period_end < second.period_start else first
        older = first if newer is second else second
        return Reconciliation(
            **{**common, "claim_ids": (newer.id, older.id), "differences": ("time_window",)},
            relationship="updates",
            state="possible_transient_change"
            if first.provisional or second.provisional
            else "temporal_update",
            interpretation=f"Claim {newer.id} describes a later, non-overlapping period. "
            "It qualifies rather than disproves the earlier finding; "
            "persistence and causality are not established.",
            confidence_adjustment=-0.10 if first.provisional or second.provisional else 0,
        )
    if (first.period_start, first.period_end) != (second.period_start, second.period_end):
        return Reconciliation(
            **{**common, "differences": ("time_window",)},
            relationship="contextualises",
            state="methodologically_incomparable",
            interpretation="The measured periods overlap but do not match. Aggregates over "
            "different windows cannot establish a direct contradiction.",
            confidence_adjustment=-0.10,
        )
    if first.provisional or second.provisional:
        return Reconciliation(
            **common,
            relationship="contextualises",
            state="possible_transient_change",
            interpretation="At least one publisher marks the finding provisional. "
            "Corroborate the observation before treating it as a durable change.",
            confidence_adjustment=-0.15,
        )
    # Independent measurements are never bit-identical; use a 1% relative
    # tolerance so near-equal values from independent studies are classified as
    # supporting rather than conflicting.
    abs_diff = abs(first.value - second.value)
    scale = max(abs(first.value), abs(second.value), 1e-12)
    rel_diff = abs_diff / scale
    agrees = abs_diff <= 1e-6 or rel_diff <= 0.01
    return Reconciliation(
        **common,
        relationship="supports" if agrees else "contradicts",
        state="compatible_support" if agrees else "material_conflict",
        interpretation=(
            "The normalized values and reported measurement contexts match. "
            "Source independence must still be assessed before boosting confidence."
            if agrees
            else "The values disagree within matching reported contexts. Preserve "
            "both estimates as contested; statistical significance is unknown "
            "without uncertainty estimates."
        ),
        confidence_adjustment=0 if agrees else -0.15,
    )


# ---------------------------------------------------------------------------
# Canonical case: Semrush/Promptwatch vs Ahrefs (Reddit citation share)
# ---------------------------------------------------------------------------

CANONICAL_SEMRUSH = StudyClaim(
    id="semrush-promptwatch-reddit-decline",
    evidence_ids=("semrush-reddits-citations-in-chatgpt-fall",),
    surface="chatgpt",
    subject="reddit.com",
    statement=(
        "Reddit's ChatGPT citation share fell from 3.8% (Jul 18 – Aug 7) to 0.5% "
        "(Aug 14–17), an 86% decline. Promptwatch flagged the observation as provisional."
    ),
    metric="citation_share",
    denominator="all ChatGPT citations",
    geography="global",
    mode="consumer_web",
    sampling_frame="daily-panel",
    period_start=date(2026, 8, 14),
    period_end=date(2026, 8, 17),
    value=0.5,
    unit="percent",
    provisional=True,
)

CANONICAL_AHREFS = StudyClaim(
    id="ahrefs-reddit-16-8-pct-sep-2026",
    evidence_ids=("ahrefs-most-cited-domains-in-chatgpt",),
    surface="chatgpt",
    subject="reddit.com",
    statement=(
        "Reddit is the largest cited domain in ChatGPT at 16.8% mention share "
        "(US, all topics, September 2026 Brand Radar snapshot)."
    ),
    metric="mention_share",
    denominator="summed citations of top sources",
    geography="US",
    mode="consumer_web",
    sampling_frame="monthly-snapshot",
    period_start=date(2026, 9, 1),
    period_end=date(2026, 9, 2),
    value=16.8,
    unit="percent",
    provisional=False,
)


def canonical_reconciliation() -> Reconciliation:
    """Reconcile the two canonical Reddit/ChatGPT studies.

    Returns the agency interpretation: methodologically incomparable (different
    denominators, geographies and time windows), not a material conflict.
    """
    return compare_claims(CANONICAL_SEMRUSH, CANONICAL_AHREFS)
