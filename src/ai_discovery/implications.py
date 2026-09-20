"""Evidence-backed marketing implications (Phase 2, issue #59).

The marketer's final question is "why does this matter, and what should I do
differently?". This module answers it *only* from validated mechanics/evidence the
product already holds. It is deliberately not a recommendation generator: there is
no free-form model output and no GEO/AEO filler. An implication exists only when a
real ledger claim supports a real mechanic that a stated rule maps to a real
action.

Design (reuses, never duplicates, the significance/POV machinery):

* **Deterministic rule table.** :data:`IMPLICATION_RULES` is an auditable
  (mechanic dimension, topic, action family) mapping. A rule fires only when the
  surface's mechanics projection carries an evidenced dimension of the named kind,
  and the firing evidence is a validated claim whose topic matches.
* **Every implication is evidence-linked.** It carries the supporting claim ids,
  the surfaces/modes/regions it applies to, a confidence, a rationale, an
  actionability/significance reading (from :func:`ai_discovery.pov.significance_of`),
  and any contradicting evidence.
* **Unknown is a valid output.** A surface with an unknown dimension produces an
  explicit ``monitor`` implication ("watch, no action yet") or nothing — never an
  invented action. Removing the supporting evidence removes the implication.
* **Cross-surface.** When several surfaces share the same evidenced mechanic, one
  implication expresses it across all of them; a surface-specific mechanic stays
  scoped to that surface.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .mechanics import MECHANICS_DIMENSIONS, SurfaceMechanics

#: The implication families issue #59 names. Each is a marketer-facing action
#: family, not a topic. ``monitor`` is the explicit no-action outcome.
ImplicationFamily = Literal[
    "crawlability_eligibility",
    "indexability_freshness",
    "citation_visibility",
    "topic_coverage",
    "structured_data_feed",
    "commerce_shopping",
    "local",
    "social_community",
    "referral_measurement",
    "platform_prioritisation",
    "monitor",
]

#: Actionability is distinct from confidence (issue #59 acceptance): a
#: high-confidence finding can still be low-actionability, and vice versa.
Actionability = Literal["high", "medium", "low"]


class ImplicationRule(BaseModel):
    """One auditable (dimension -> action family) rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    family: ImplicationFamily
    dimension: str
    #: The claim topic that must be present for the rule to fire. A mechanic on the
    #: dimension from a *different* topic (e.g. an audience claim) does not fire it.
    topic: str
    #: The restrained, marketer-readable action text. Written once, here — never by
    #: a model, and never a generic GEO/AEO instruction.
    action: str
    #: Why this action follows from this mechanic, in marketer terms.
    rationale: str


#: The rule table. Every rule names a canonical mechanics dimension and the ledger
#: topic that evidences it. A dimension absent here produces no implication.
IMPLICATION_RULES: tuple[ImplicationRule, ...] = (
    ImplicationRule(
        family="crawlability_eligibility",
        dimension="crawling_indexing_controls",
        topic="crawler_index_policy",
        action=(
            "Confirm the crawler user-agents named in the vendor documentation are "
            "allowed in robots.txt, and that any disallow is deliberate."
        ),
        rationale="The surface's crawler controls are vendor-documented, so eligibility is a decision you control.",
    ),
    ImplicationRule(
        family="crawlability_eligibility",
        dimension="marketer_controllable_inputs",
        topic="crawler_index_policy",
        action="Audit the site-side signals the surface documents (robots directives, markup, feeds) against your current configuration.",
        rationale="The surface documents signals a marketer can change, so they are actionable inputs, not fixed behaviour.",
    ),
    ImplicationRule(
        family="indexability_freshness",
        dimension="freshness_recrawl",
        topic="crawler_index_policy",
        action="Align update cadence with the documented recrawl window so time-sensitive content is refreshed within it.",
        rationale="A documented freshness/recrawl mechanic sets how quickly changed content can be reflected.",
    ),
    ImplicationRule(
        family="citation_visibility",
        dimension="citation_presentation",
        topic="citations_sources",
        action="Treat citations as a first-class outcome: track which pages are cited and structure content to be quotable.",
        rationale="The surface's citation presentation is evidenced, so source visibility is a measurable outcome.",
    ),
    ImplicationRule(
        family="citation_visibility",
        dimension="social_community_retrieval",
        topic="citations_sources",
        action="Assess whether community/forum sources are being retrieved for your topics and whether your presence there is defensible.",
        rationale="Evidence shows social/community sources are retrieved, so community presence can affect citations.",
    ),
    ImplicationRule(
        family="topic_coverage",
        dimension="query_rewrite",
        topic="retrieval_index",
        action="Map queries to the fan-out sub-queries the surface decomposes into, and cover the entities each sub-query implies.",
        rationale="An evidenced query-rewrite/fan-out mechanic means coverage is judged per sub-query, not per head term.",
    ),
    ImplicationRule(
        family="structured_data_feed",
        dimension="shopping_product_feed",
        topic="commerce_ads",
        action="Ensure product/catalogue feeds and structured markup are complete for the categories the surface can surface.",
        rationale="An evidenced shopping/feed mechanic makes feed and structured-data completeness actionable.",
    ),
    ImplicationRule(
        family="commerce_shopping",
        dimension="shopping_product_feed",
        topic="commerce_ads",
        action="Review whether commercial placement on the surface changes your category's visibility and measurement.",
        rationale="The surface exposes commerce/product surfaces, so shopping visibility is a distinct outcome.",
    ),
    ImplicationRule(
        family="local",
        dimension="local_retrieval",
        topic="retrieval_index",
        action="Keep local/place data accurate where the surface retrieves local sources.",
        rationale="Evidence shows local/place retrieval, so local data accuracy can affect eligibility.",
    ),
    ImplicationRule(
        family="referral_measurement",
        dimension="answer_type",
        topic="referrals_conversion",
        action="Separate AI-referral traffic from organic in measurement so AI-driven visits are not misattributed.",
        rationale="An evidenced referral/conversion mechanic means AI referral is measurable and worth isolating.",
    ),
    ImplicationRule(
        family="platform_prioritisation",
        dimension="mode_region_differences",
        topic="audience_usage",
        action="Prioritise surfaces and regions by evidenced reach rather than by assumption.",
        rationale="Evidenced mode/region differences mean priority should follow measured reach per market.",
    ),
)


class Implication(BaseModel):
    """One evidence-linked marketing implication."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    family: ImplicationFamily
    action: str
    rationale: str
    #: The evidence this implication rests on. Empty only for a ``monitor`` result.
    supporting_claim_ids: tuple[str, ...] = ()
    supporting_dimensions: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    modes: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    confidence: str
    #: Distinct from confidence: how much a marketer can actually do about it.
    actionability: Actionability
    significance: float
    #: Contradicting evidence, when the supporting claims are contested.
    contradicting_claim_ids: tuple[str, ...] = ()
    #: True for the explicit no-action outcome.
    monitor_only: bool = False
    note: str = ""


def _confidence_rank(value: str) -> int:
    return {"unknown": 0, "low": 1, "medium": 2, "high": 3}.get(str(value), 0)


def _actionability(dimension: str, topic: str) -> Actionability:
    """How much a marketer can act on a dimension (deterministic, stated here)."""

    if dimension in ("crawling_indexing_controls", "marketer_controllable_inputs", "freshness_recrawl"):
        return "high"
    if dimension in ("citation_presentation", "shopping_product_feed", "query_rewrite", "social_community_retrieval", "local_retrieval"):
        return "medium"
    # Knowledge about provider/selection/answer-type is useful but not directly actionable.
    return "low"


def surface_implications(
    surface_id: str,
    mechanics: SurfaceMechanics,
    claims: list[dict[str, Any]],
    *,
    scorer: Any | None = None,
    policy: Any | None = None,
) -> list[Implication]:
    """Derive implications for one surface from its evidenced mechanics.

    A rule fires only when (a) the surface's projection has an evidenced (non-
    ``unknown``) dimension equal to the rule's, and (b) a real claim on that
    surface has the rule's topic and lights that dimension. The supporting claim
    ids and their scope are taken from the proposal evidence, so removing the
    evidence removes the implication.
    """

    from .pov import significance_of

    by_claim = {c.get("claim_id"): c for c in claims}
    out: list[Implication] = []

    for rule in IMPLICATION_RULES:
        try:
            dim = mechanics.dimension(rule.dimension)
        except KeyError:
            continue
        if dim.state == "unknown":
            continue
        # Gather the evidence on this dimension whose claim carries the rule topic.
        #
        # ``supersedes`` is REPLACEMENT, not disagreement (issue #59 review
        # impl-001): a superseding claim retires the claim it replaces rather than
        # contradicting it, so the superseded claim is dropped from support and does
        # NOT cap confidence. Only an explicit ``contradicts`` (or a ``contested``
        # status) is a live disagreement. Scope (modes/regions) is unioned from
        # supporting evidence only — a superseded or contradicting claim must not
        # widen where the implication claims to apply.
        superseded: set[str] = set()
        for assertion in dim.assertions:
            for ev in assertion.evidence:
                if ev.relationship == "supersedes" and ev.relates_to_claim_id:
                    superseded.add(ev.relates_to_claim_id)

        supporting: list[str] = []
        contradicting: list[str] = []
        modes: set[str] = set()
        regions: set[str] = set()
        for assertion in dim.assertions:
            for ev in assertion.evidence:
                row = by_claim.get(ev.claim_id)
                if row is None or row.get("topic") != rule.topic:
                    continue
                if ev.claim_id in superseded:
                    # Replaced by a newer reading: not support, not a contradiction.
                    continue
                if ev.relationship == "contradicts" or row.get("status") == "contested":
                    contradicting.append(ev.claim_id)
                    continue
                supporting.append(ev.claim_id)
                modes.update(ev.modes)
                regions.update(ev.regions)
        if not supporting:
            continue

        # Confidence: the weakest supporting claim governs, and any contradiction
        # caps the reading at the lowest supporting level (never hidden).
        confidences = [by_claim[c]["confidence"] for c in supporting]
        confidence = min(confidences, key=_confidence_rank)
        if contradicting:
            confidence = min(confidence, "low", key=_confidence_rank)

        # Significance reuses the tested POV machinery on the lead claim.
        lead = by_claim[supporting[0]]
        try:
            significance = significance_of(lead, scorer=scorer, policy=policy)
        except (ValueError, KeyError, TypeError):  # pragma: no cover - defensive read path
            significance = 0.0

        out.append(
            Implication(
                family=rule.family,
                action=rule.action,
                rationale=rule.rationale,
                supporting_claim_ids=tuple(dict.fromkeys(supporting)),
                supporting_dimensions=(rule.dimension,),
                surfaces=(surface_id,),
                modes=tuple(sorted(modes)),
                regions=tuple(sorted(regions)),
                confidence=confidence,
                actionability=_actionability(rule.dimension, rule.topic),
                significance=significance,
                contradicting_claim_ids=tuple(dict.fromkeys(contradicting)),
            )
        )
    return out


class SurfaceImplications(BaseModel):
    """The implication set for one surface, with the explicit no-action state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface_id: str
    implications: tuple[Implication, ...] = ()
    #: Set when there is no evidenced, topic-matched mechanic to act on.
    monitor_only: bool = False
    note: str = ""

    @property
    def evidenced(self) -> bool:
        """True when the surface has at least one *actionable* implication.

        A monitor implication is a structured no-action result, so it does not make
        the surface "evidenced" for the purpose of action.
        """

        return any(not i.monitor_only for i in self.implications)


def derive_surface(
    surface_id: str,
    mechanics: SurfaceMechanics,
    claims: list[dict[str, Any]],
    *,
    scorer: Any | None = None,
    policy: Any | None = None,
) -> SurfaceImplications:
    """Implications for one surface, or an explicit monitor-only state.

    ``monitor_only`` is a first-class, correct answer: a surface whose mechanics
    are all unknown, or whose evidenced mechanics match no action rule, gets an
    explicit "watch, no action yet" result rather than invented advice.
    """

    implications = surface_implications(
        surface_id, mechanics, claims, scorer=scorer, policy=policy
    )
    if implications:
        return SurfaceImplications(surface_id=surface_id, implications=tuple(implications))
    # No actionable evidenced mechanic. Emit a structured monitor Implication so
    # the no-action outcome has the same shape as an action (issue #59 review
    # impl-003): it states why nothing is recommended and names the unknown
    # dimensions being watched, with no invented evidence.
    unknown_dims = tuple(
        d.dimension for d in mechanics.dimensions if d.state == "unknown"
    )
    note = (
        "No evidenced, marketer-actionable mechanic for this surface yet. "
        "Monitor rather than act: unknown is a valid answer."
    )
    monitor = Implication(
        family="monitor",
        action="Monitor this surface; do not act on assumption until a mechanic is evidenced.",
        rationale=(
            "The evidence does not yet support a specific action for this surface, so "
            "taking one would be a guess. Watching for validated mechanics is the "
            "correct next step."
        ),
        supporting_claim_ids=(),
        supporting_dimensions=(),
        surfaces=(surface_id,),
        confidence="unknown",
        actionability="low",
        significance=0.0,
        monitor_only=True,
        note=note + (f" Watching {len(unknown_dims)} unknown dimension(s)." if unknown_dims else ""),
    )
    return SurfaceImplications(
        surface_id=surface_id,
        implications=(monitor,),
        monitor_only=True,
        note=note,
    )


def cross_surface_implications(
    per_surface: dict[str, SurfaceImplications],
) -> list[Implication]:
    """Merge the same (family, dimension) implication across surfaces.

    Issue #59 acceptance: a mechanic several surfaces share should be expressible
    once, across all of them, while a surface-specific mechanic stays scoped. Two
    implications merge only when they share the action family and dimension; their
    surfaces, regions and claim ids are unioned.
    """

    grouped: dict[tuple[str, tuple[str, ...]], list[Implication]] = {}
    for impl_set in per_surface.values():
        for impl in impl_set.implications:
            # Monitor results are per-surface no-action states, not actions to
            # merge: they stay in the per-surface payload only (review impl-003).
            if impl.monitor_only:
                continue
            key = (impl.family, impl.supporting_dimensions)
            grouped.setdefault(key, []).append(impl)

    merged: list[Implication] = []
    for members in grouped.values():
        if len(members) == 1:
            merged.append(members[0])
            continue
        surfaces = tuple(sorted({s for m in members for s in m.surfaces}))
        supporting = tuple(dict.fromkeys(c for m in members for c in m.supporting_claim_ids))
        contradicting = tuple(dict.fromkeys(c for m in members for c in m.contradicting_claim_ids))
        modes = tuple(sorted({x for m in members for x in m.modes}))
        regions = tuple(sorted({x for m in members for x in m.regions}))
        confidence = min((m.confidence for m in members), key=_confidence_rank)
        # Do not overstate on merge (issue #59 review impl-002): the merged
        # significance is the WEAKEST member's, matching the min-policy used for
        # confidence and actionability. A merged implication claims to apply across
        # all its surfaces, so it may not inherit the strongest surface's reading.
        significance = min(m.significance for m in members)
        # Actionability is the least actionable of the merged set (do not overstate).
        order = {"high": 3, "medium": 2, "low": 1}
        actionability = min(members, key=lambda m: order[m.actionability]).actionability
        merged.append(
            members[0].model_copy(
                update={
                    "surfaces": surfaces,
                    "supporting_claim_ids": supporting,
                    "contradicting_claim_ids": contradicting,
                    "modes": modes,
                    "regions": regions,
                    "confidence": confidence,
                    "significance": significance,
                    "actionability": actionability,
                    "note": f"Applies across {len(surfaces)} surfaces that share this evidenced mechanic.",
                }
            )
        )
    # Stable order: actionable + significant first, monitor last.
    merged.sort(key=lambda i: (i.monitor_only, -i.significance, i.family))
    return merged


def implication_view(impl: Implication) -> dict[str, Any]:
    """The marketer-safe payload for one implication."""

    return {
        "family": impl.family,
        "action": impl.action,
        "rationale": impl.rationale,
        "supporting_claim_ids": list(impl.supporting_claim_ids),
        "supporting_dimensions": list(impl.supporting_dimensions),
        "surfaces": list(impl.surfaces),
        "modes": list(impl.modes),
        "regions": list(impl.regions),
        "confidence": impl.confidence,
        "actionability": impl.actionability,
        "significance": impl.significance,
        "contradicting_claim_ids": list(impl.contradicting_claim_ids),
        "monitor_only": impl.monitor_only,
        "note": impl.note,
    }


def implications_view(result: dict[str, SurfaceImplications]) -> dict[str, Any]:
    """The bulk payload: per-surface sets plus the merged cross-surface list."""

    merged = cross_surface_implications(result)
    return {
        "count": len(merged),
        "surfaces": {
            sid: {
                "surface": s.surface_id,
                "monitor_only": s.monitor_only,
                "note": s.note,
                "implications": [implication_view(i) for i in s.implications],
            }
            for sid, s in result.items()
        },
        "cross_surface": [implication_view(i) for i in merged],
    }


#: The canonical dimension set the rules reference, exposed for audit/tests.
RULE_DIMENSIONS: tuple[str, ...] = tuple(dict.fromkeys(r.dimension for r in IMPLICATION_RULES))
assert set(RULE_DIMENSIONS) <= set(MECHANICS_DIMENSIONS)
