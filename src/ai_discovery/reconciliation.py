"""Compare study contexts before interpreting a numerical disagreement.

This module returns a separate agency interpretation. Source claims are immutable;
it never replaces a measured value or treats an unknown context as a match.
"""
from datetime import date
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Relationship = Literal["supports", "updates", "contradicts", "supersedes", "contextualises"]
ConflictState = Literal[
    "compatible_support", "directional_support", "methodologically_incomparable",
    "temporal_update", "material_conflict", "possible_transient_change", "unresolved",
]


class StudyClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    surface: str
    subject: str  # E.g. reddit.com; two different cited domains aren't a conflict.
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

    @model_validator(mode="after")
    def valid_measurement(self):
        if self.value is not None and not isfinite(self.value):
            raise ValueError("Measurement must be finite")
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("Study period ends before it starts")
        return self


class Reconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)
    claim_ids: tuple[str, str]
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
    context = ("surface", "subject", "metric", "denominator", "geography", "mode",
               "sampling_frame", "unit")
    differences = tuple(
        key for key in context
        if getattr(first, key) is not None and getattr(second, key) is not None
        and getattr(first, key) != getattr(second, key)
    )
    unknown = tuple(
        key for key in (*context, "period_start", "period_end", "value")
        if getattr(first, key) is None or getattr(second, key) is None
    )
    common = dict(
        claim_ids=(first.id, second.id),
        evidence_ids=tuple(dict.fromkeys((*first.evidence_ids, *second.evidence_ids))),
        differences=differences, unknown_dimensions=unknown,
    )
    if differences:
        return Reconciliation(
            **common, relationship="contextualises", state="methodologically_incomparable",
            interpretation=(
                f"These findings differ in {', '.join(differences)} and cannot be reconciled "
                "as estimates of the same quantity. Preserve both findings in their stated "
                "contexts; neither establishes a universal change or absence of change."
                + (" At least one publisher marks its finding provisional." if
                   first.provisional or second.provisional else "")
            ), confidence_adjustment=-0.15,
        )
    if unknown:
        return Reconciliation(
            **common, relationship="contextualises", state="unresolved",
            interpretation=f"Insufficient context to compare: {', '.join(unknown)}. "
                           "Missing methodology is not evidence of agreement or contradiction.",
            confidence_adjustment=-0.15,
        )
    # All dates and values are known after the conservative missing-data branch.
    assert first.period_start and first.period_end and second.period_start and second.period_end
    if first.period_end < second.period_start or second.period_end < first.period_start:
        newer = second if first.period_end < second.period_start else first
        return Reconciliation(
            **{**common, "differences": ("time_window",)}, relationship="updates",
            state="possible_transient_change" if first.provisional or second.provisional
            else "temporal_update",
            interpretation=f"Claim {newer.id} describes a later, non-overlapping period. "
                           "It qualifies rather than disproves the earlier finding; "
                           "persistence and causality are not established.",
            confidence_adjustment=-0.10 if first.provisional or second.provisional else 0,
        )
    if (first.period_start, first.period_end) != (second.period_start, second.period_end):
        return Reconciliation(
            **{**common, "differences": ("time_window",)}, relationship="contextualises",
            state="methodologically_incomparable",
            interpretation="The measured periods overlap but do not match. Aggregates over "
                           "different windows cannot establish a direct contradiction.",
            confidence_adjustment=-0.10,
        )
    if first.provisional or second.provisional:
        return Reconciliation(
            **common, relationship="contextualises", state="possible_transient_change",
            interpretation="At least one publisher marks the finding provisional. "
                           "Corroborate the observation before treating it as a durable change.",
            confidence_adjustment=-0.15,
        )
    agrees = first.value == second.value
    return Reconciliation(
        **common, relationship="supports" if agrees else "contradicts",
        state="compatible_support" if agrees else "material_conflict",
        interpretation=("The normalized values and reported measurement contexts match. "
                        "Source independence must still be assessed before boosting confidence."
                        if agrees else
                        "The values disagree within matching reported contexts. Preserve "
                        "both estimates as contested; statistical significance is unknown "
                        "without uncertainty estimates."),
        confidence_adjustment=0 if agrees else -0.15,
    )
