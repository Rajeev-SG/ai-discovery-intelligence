"""Canonical discovery-mechanics ontology and evidence contract (Phase 2, issue #56).

The registry's coarse ``discovery_modes`` + one ``retrieval_status`` enum cannot
explain *how* an AI discovery surface actually finds, retrieves and cites
information, and generic copy derived from a status enum is not intelligence.

This module defines the canonical, typed mechanics model every surface is
projected through. Per surface it models thirteen independent mechanics
dimensions, each carrying its own *state*:

- ``known``            - at least one non-conflicting, evidenced assertion;
- ``partially_known``  - evidence exists but is explicitly partial/scoped;
- ``conflicting``      - two or more evidenced assertions disagree;
- ``unknown``          - no evidence exists; a first-class, correct answer.

Crucially, **evidence is not invented here**. Every non-``unknown`` mechanics
assertion must name a real ledger claim. This module never reads the registry's
``retrieval_status`` as evidence, never reads model knowledge, and never invents
a mechanic to fill a cell: the projection takes *already-validated claims* as its
only evidence input, and any dimension with no supporting claim becomes
``unknown``. It also never manufactures assertions from registry metadata: claims
are linked to a dimension by an explicit, auditable mapping (``DIMENSION_TOPICS``)
and a topic with no mapping contributes nothing.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --------------------------------------------------------------------------- #
# Dimensions (the canonical, frozen set required by issue #56)
# --------------------------------------------------------------------------- #

MechanicsDimension = Literal[
    "search_trigger",
    "retrieval_provider",
    "query_rewrite",
    "crawling_indexing_controls",
    "freshness_recrawl",
    "candidate_selection_reranking",
    "citation_presentation",
    "shopping_product_feed",
    "local_retrieval",
    "social_community_retrieval",
    "mode_region_differences",
    "answer_type",
    "marketer_controllable_inputs",
]

MECHANICS_DIMENSIONS: tuple[str, ...] = (
    "search_trigger",
    "retrieval_provider",
    "query_rewrite",
    "crawling_indexing_controls",
    "freshness_recrawl",
    "candidate_selection_reranking",
    "citation_presentation",
    "shopping_product_feed",
    "local_retrieval",
    "social_community_retrieval",
    "mode_region_differences",
    "answer_type",
    "marketer_controllable_inputs",
)

#: Human label + one-line definition per dimension. This is presentation copy
#: *about the model*, not a claim about any surface.
DIMENSION_META: dict[str, dict[str, str]] = {
    "search_trigger": {
        "label": "Search / retrieval trigger",
        "definition": "When and why the surface decides to retrieve from the live "
        "web rather than answer from model weights.",
    },
    "retrieval_provider": {
        "label": "Retrieval provider / index",
        "definition": "Which index or upstream search provider backs retrieval.",
    },
    "query_rewrite": {
        "label": "Query rewrite / fan-out",
        "definition": "Whether and how the user query is rewritten, decomposed or "
        "fanned out into multiple sub-queries.",
    },
    "crawling_indexing_controls": {
        "label": "Crawling and indexing controls",
        "definition": "Crawler user-agents, robots directives and site-side controls "
        "that govern what is fetched and indexed.",
    },
    "freshness_recrawl": {
        "label": "Freshness / recrawl",
        "definition": "How quickly changed content is refetched and reflected.",
    },
    "candidate_selection_reranking": {
        "label": "Candidate selection / reranking",
        "definition": "How retrieved candidates are filtered, ranked or reranked "
        "before an answer is composed.",
    },
    "citation_presentation": {
        "label": "Citation / source presentation",
        "definition": "Whether sources are shown, and in what form (inline links, "
        "cards, footnotes, absent).",
    },
    "shopping_product_feed": {
        "label": "Shopping / product feed",
        "definition": "Product, catalogue or feed behaviour in commercial results.",
    },
    "local_retrieval": {
        "label": "Local retrieval",
        "definition": "Use of local/place retrieval or map data.",
    },
    "social_community_retrieval": {
        "label": "Social / community retrieval",
        "definition": "Use of social, forum or community sources (e.g. Reddit).",
    },
    "mode_region_differences": {
        "label": "Mode / model / account / region differences",
        "definition": "How behaviour differs across modes, models, account tiers or regions.",
    },
    "answer_type": {
        "label": "Direct vs retrieval-backed answer",
        "definition": "Whether a response is a direct model answer or grounded in "
        "retrieved sources.",
    },
    "marketer_controllable_inputs": {
        "label": "Marketer-controllable eligibility inputs",
        "definition": "Signals a marketer can change (markup, feeds, robots policy, "
        "content structure) that affect eligibility.",
    },
}

MechanicsState = Literal["known", "partially_known", "conflicting", "unknown"]
MECHANICS_STATES: tuple[str, ...] = ("known", "partially_known", "conflicting", "unknown")


# --------------------------------------------------------------------------- #
# Topic -> dimension mapping (explicit; never inferred from model knowledge)
# --------------------------------------------------------------------------- #
#
# A claim's ledger ``topic`` is coarse. This mapping is the single, auditable
# statement of which mechanics dimension(s) a topic is *about*. A topic absent
# from this map contributes no mechanics evidence for any dimension. The mapping
# is many-to-many: one topic may inform more than one dimension.
DIMENSION_TOPICS: dict[str, tuple[str, ...]] = {
    "search_trigger": ("retrieval_index",),
    "retrieval_provider": ("retrieval_index",),
    "query_rewrite": ("retrieval_index",),
    "crawling_indexing_controls": ("crawler_index_policy",),
    "freshness_recrawl": ("crawler_index_policy", "retrieval_index"),
    "candidate_selection_reranking": ("retrieval_index",),
    "citation_presentation": ("citations_sources",),
    "shopping_product_feed": ("commerce_ads",),
    "local_retrieval": ("retrieval_index",),
    # A coarse ``citations_sources`` claim is about citation *share*, not about
    # whether a surface sources from social/community pages. At topic granularity
    # that mapping would assert something the topic cannot evidence, so it is
    # deliberately absent: with no social-specific topic the dimension stays an
    # honest ``unknown`` rather than a derived guess.
    "social_community_retrieval": (),
    "mode_region_differences": ("retrieval_index",),
    "answer_type": ("retrieval_index",),
    "marketer_controllable_inputs": (
        "optimisation_implication",
        "crawler_index_policy",
        "commerce_ads",
    ),
}

#: Topics that are explicitly *not* mechanics evidence. Named so the audit trail
#: can say why a topic was ignored rather than only that it was. An audience or
#: market-share claim must never masquerade as a statement about *how* a surface
#: retrieves - that is the exact "looks like a market-share tracker" anti-pattern
#: issue #57 names.
NON_MECHANICS_TOPICS: frozenset[str] = frozenset(
    {"audience_usage", "referrals_conversion", "measurement"}
)


# --------------------------------------------------------------------------- #
# Evidence reference carried by a mechanics assertion
# --------------------------------------------------------------------------- #

#: Source classes projected into the three marketer-facing evidence classes
#: required by issues #57/#58. Kept here (not in React) so backend and frontend
#: agree by construction.
EVIDENCE_CLASS_BY_SOURCE_CLASS: dict[str, str] = {
    "official": "official_documentation",
    "vendor_research": "official_documentation",
    "vendor_blog": "official_documentation",
    "press_release": "official_documentation",
    "market_telemetry": "independent_research",
    "visibility_research": "independent_research",
    "open_research": "independent_research",
    "industry_report": "independent_research",
    "editorial_discovery": "independent_research",
    "news": "independent_research",
    "open_discovery": "independent_research",
    "controlled_observation": "controlled_observation",
    "other": "independent_research",
}

EvidenceClass = Literal["official_documentation", "independent_research", "controlled_observation"]


def evidence_class_for(source_class: str) -> str:
    """Map a ledger source class to the marketer-facing evidence class."""

    return EVIDENCE_CLASS_BY_SOURCE_CLASS.get(source_class, "independent_research")


class MechanicsEvidence(BaseModel):
    """One evidenced link supporting a mechanics assertion.

    The evidence contract from issue #56: claim/evidence IDs, source class,
    dates, confidence, methodology/provenance, applicable surface/mode/region,
    and conflicts/supersession where present. Every value here is copied from a
    real ledger claim - nothing is synthesised.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1)
    source_id: str | None = None
    publisher: str | None = None
    url: str | None = None
    source_class: str
    evidence_class: str
    #: The three dates the contract distinguishes. Any may be absent (unknown).
    published_at: dt.date | None = None
    observed_at: dt.datetime | None = None
    effective_from: dt.date | None = None
    confidence: str
    confidence_score: float | None = None
    measurement_mode: str | None = None
    methodology_notes: str | None = None
    limitations: tuple[str, ...] = ()
    #: Scope the evidence applies to, so a mode/region-specific fact is not
    #: silently generalised to the whole surface.
    modes: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    relates_to_claim_id: str | None = None
    relationship: str = "new"

    @model_validator(mode="after")
    def _class_matches_source(self) -> MechanicsEvidence:
        expected = evidence_class_for(self.source_class)
        if self.evidence_class != expected:
            raise ValueError(
                f"evidence_class {self.evidence_class!r} does not match "
                f"source_class {self.source_class!r} (expected {expected!r})"
            )
        return self


class MechanicsAssertion(BaseModel):
    """A marketer-readable statement about one dimension of one surface, evidenced."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str = Field(min_length=1)
    state: MechanicsState
    evidence: tuple[MechanicsEvidence, ...] = Field(min_length=1)
    #: Set only when the ledger explicitly marks a conflicts/supersedes relation.
    conflict_note: str | None = None

    @model_validator(mode="after")
    def _state_matches_evidence(self) -> MechanicsAssertion:
        if self.state == "unknown":
            raise ValueError(
                "an unknown mechanics assertion is expressed by DimensionState, not an assertion"
            )
        return self


class DimensionState(BaseModel):
    """The state of one mechanics dimension for one surface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dimension: str
    state: MechanicsState
    assertions: tuple[MechanicsAssertion, ...] = ()
    #: Why the state is what it is - always populated, never a silent empty cell.
    note: str = ""

    @model_validator(mode="after")
    def _consistent(self) -> DimensionState:
        if self.dimension not in MECHANICS_DIMENSIONS:
            raise ValueError(f"unknown mechanics dimension {self.dimension!r}")
        if self.state == "unknown":
            if self.assertions:
                raise ValueError("state=unknown must not carry assertions")
            if not self.note:
                raise ValueError(
                    "state=unknown requires an explicit note (unknown is an answer, not a blank cell)"
                )
        else:
            if not self.assertions:
                raise ValueError(f"state={self.state} requires at least one evidenced assertion")
        return self

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(e.claim_id for a in self.assertions for e in a.evidence)


class SurfaceMechanics(BaseModel):
    """The complete canonical mechanics projection for one surface."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface_id: str = Field(min_length=1)
    dimensions: tuple[DimensionState, ...]

    @model_validator(mode="after")
    def _complete(self) -> SurfaceMechanics:
        present = {d.dimension for d in self.dimensions}
        missing = set(MECHANICS_DIMENSIONS) - present
        if missing:
            raise ValueError(
                f"surface {self.surface_id} projection must cover every dimension; "
                f"missing {sorted(missing)}"
            )
        if len(present) != len(self.dimensions):
            raise ValueError("duplicate dimension in projection")
        return self

    def dimension(self, name: str) -> DimensionState:
        for d in self.dimensions:
            if d.dimension == name:
                return d
        raise KeyError(name)

    def state_of(self, name: str) -> str:
        return self.dimension(name).state

    def coverage(self) -> dict[str, int]:
        """Count of dimensions per state - the surface's mechanics coverage summary."""

        out = {s: 0 for s in MECHANICS_STATES}
        for d in self.dimensions:
            out[d.state] += 1
        return out

    def evidenced_dimension_count(self) -> int:
        return sum(1 for d in self.dimensions if d.state != "unknown")


# --------------------------------------------------------------------------- #
# Projection: validated claims -> canonical mechanics
# --------------------------------------------------------------------------- #


def _iso_date(value: Any) -> dt.date | None:
    if not value:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _evidence_from_claim(row: dict[str, Any]) -> MechanicsEvidence | None:
    """Build a MechanicsEvidence from one expanded-claim read row.

    Returns ``None`` when the row lacks the minimum a claim needs to be evidence
    (an id and a source class); a malformed row is skipped rather than turned
    into a fabricated assertion.
    """

    source = row.get("source") or {}
    source_class = source.get("source_class")
    if not source_class or not row.get("claim_id"):
        return None
    methodology = row.get("methodology") or {}
    dates = row.get("dates") or {}
    observed = dates.get("observed_at")
    parsed_observed = None
    if observed:
        try:
            parsed_observed = dt.datetime.fromisoformat(str(observed))
        except ValueError:
            parsed_observed = None

    # Scope the evidence applies to. Only what the claim itself states travels
    # with the evidence: a surface's registry regions are NOT asserted here, since
    # that would convert registry metadata into evidence.
    regions: tuple[str, ...] = ()
    geo = methodology.get("geography")
    if geo:
        regions = (str(geo),)

    return MechanicsEvidence(
        claim_id=row["claim_id"],
        source_id=source.get("source_id"),
        publisher=source.get("publisher"),
        url=source.get("url"),
        source_class=source_class,
        evidence_class=evidence_class_for(source_class),
        published_at=_iso_date(dates.get("published_at")),
        observed_at=parsed_observed,
        confidence=row.get("confidence") or "unknown",
        confidence_score=(row.get("confidence_detail") or {}).get("score"),
        measurement_mode=methodology.get("measurement_mode"),
        methodology_notes=methodology.get("methodology_notes"),
        limitations=tuple(methodology.get("limitations") or ()),
        regions=regions,
        relationship=row.get("relationship") or "new",
        relates_to_claim_id=row.get("supersedes_claim_id"),
    )


def _claims_for(
    claims: list[dict[str, Any]],
    surface_id: str,
    dimension: str,
) -> list[dict[str, Any]]:
    """Real claims that (a) name this surface and (b) whose topic maps to this dimension."""

    from .registry import resolve_surface_id

    topics = set(DIMENSION_TOPICS.get(dimension, ()))
    if not topics:
        return []
    out: list[dict[str, Any]] = []
    for row in claims:
        # Resolve the claim's surface value to a canonical id (read-time only;
        # the stored claim is never rewritten). An unaliased value that is not a
        # real surface never attaches.
        row_surfaces = {resolve_surface_id(s) for s in (row.get("surfaces") or [])}
        if surface_id not in row_surfaces:
            continue
        if row.get("topic") in topics:
            out.append(row)
    return out


def _assertion_from_claims(
    rows: list[dict[str, Any]],
) -> MechanicsAssertion | None:
    """One evidenced assertion from one or more claims sharing a dimension.

    When two or more claims carry an explicit ``contradicts``/``supersedes``
    relationship (or a claim is marked ``contested``), the dimension is
    ``conflicting``; otherwise evidence is ``known`` unless a claim is marked
    ``watch``, in which case it is ``partially_known``.
    """

    evidences: list[MechanicsEvidence] = []
    for row in rows:
        ev = _evidence_from_claim(row)
        if ev is not None:
            evidences.append(ev)
    if not evidences:
        return None

    conflicting = any(
        (row.get("relationship") in {"contradicts", "supersedes"})
        or row.get("status") == "contested"
        for row in rows
    )
    partial = any(row.get("status") == "watch" for row in rows)

    # A single representative statement: the first claim's statement. We never
    # merge claims into new prose - the assertion *is* the claim's own statement.
    statement = rows[0].get("statement") or ""
    if not statement:
        return None

    if conflicting:
        state: MechanicsState = "conflicting"
        conflict_note = "Evidence for this dimension disagrees across sources; both are preserved."
    elif partial:
        state = "partially_known"
        conflict_note = None
    else:
        state = "known"
        conflict_note = None

    return MechanicsAssertion(
        statement=statement.strip(),
        state=state,
        evidence=tuple(evidences),
        conflict_note=conflict_note,
    )


def project_surface(surface_id: str, claims: list[dict[str, Any]]) -> SurfaceMechanics:
    """Project one surface through the canonical mechanics contract from real claims.

    Every dimension is emitted. A dimension with no supporting, mapped claim is
    ``unknown`` - explicitly, with a note - rather than omitted or inferred.
    """

    states: list[DimensionState] = []
    for dimension in MECHANICS_DIMENSIONS:
        rows = [r for r in _claims_for(claims, surface_id, dimension) if r.get("statement")]
        if not rows:
            if not DIMENSION_TOPICS.get(dimension):
                note = (
                    "No evidenced mechanics dimension maps to this surface yet; "
                    "the ledger holds no claim kind that speaks to it."
                )
            else:
                note = (
                    "No validated claim for this surface covers this dimension. "
                    "Unknown is a valid, explicit answer, not a missing value."
                )
            states.append(DimensionState(dimension=dimension, state="unknown", note=note))
            continue
        assertion = _assertion_from_claims(rows)
        if assertion is None:
            states.append(
                DimensionState(
                    dimension=dimension,
                    state="unknown",
                    note="Mapped claims exist but none is usable as mechanics evidence.",
                )
            )
            continue
        states.append(
            DimensionState(
                dimension=dimension,
                state=assertion.state,
                assertions=(assertion,),
                note="",
            )
        )
    return SurfaceMechanics(surface_id=surface_id, dimensions=tuple(states))


def project_all(
    surface_ids: list[str],
    claims: list[dict[str, Any]],
) -> dict[str, SurfaceMechanics]:
    """Project every surface id through the canonical contract."""

    return {sid: project_surface(sid, claims) for sid in surface_ids}


# --------------------------------------------------------------------------- #
# Marketer-safe serialisation (no private snapshot data, no capture text)
# --------------------------------------------------------------------------- #


def dimension_view(state: DimensionState) -> dict[str, Any]:
    """The marketer-safe view of one mechanics dimension."""

    meta = DIMENSION_META.get(state.dimension, {})
    return {
        "dimension": state.dimension,
        "label": meta.get("label", state.dimension),
        "definition": meta.get("definition", ""),
        "state": state.state,
        "note": state.note,
        "assertions": [
            {
                "statement": a.statement,
                "state": a.state,
                "conflict_note": a.conflict_note,
                "evidence": [
                    {
                        "claim_id": e.claim_id,
                        "source_id": e.source_id,
                        "publisher": e.publisher,
                        "url": e.url,
                        "source_class": e.source_class,
                        "evidence_class": e.evidence_class,
                        "published_at": e.published_at.isoformat() if e.published_at else None,
                        "observed_at": e.observed_at.isoformat() if e.observed_at else None,
                        "effective_from": e.effective_from.isoformat() if e.effective_from else None,
                        "confidence": e.confidence,
                        "confidence_score": e.confidence_score,
                        "measurement_mode": e.measurement_mode,
                        "methodology_notes": e.methodology_notes,
                        "limitations": list(e.limitations),
                        "modes": list(e.modes),
                        "regions": list(e.regions),
                        "relates_to_claim_id": e.relates_to_claim_id,
                        "relationship": e.relationship,
                    }
                    for e in a.evidence
                ],
            }
            for a in state.assertions
        ],
    }


def unmapped_claim_surfaces(
    surface_ids: list[str], claims: list[dict[str, Any]]
) -> dict[str, list[str]]:
    """Claim surface ids that are not in the canonical registry.

    A claim may name a surface id the registry does not carry (a data-integrity
    drift, e.g. a regional alias). Those claims are never silently attached to a
    real surface: they are reported so the drift is visible and fixable. This is
    a diagnostic, not evidence.
    """

    from .registry import SURFACE_ALIASES

    known = set(surface_ids)
    seen: dict[str, set[str]] = {}
    for row in claims:
        for raw_sid in row.get("surfaces") or []:
            # An aliased value resolves to a real surface, so it is not drift.
            if raw_sid in known or raw_sid in SURFACE_ALIASES:
                continue
            seen.setdefault(raw_sid, set()).add(row.get("claim_id") or "")
    return {sid: sorted(ids) for sid, ids in sorted(seen.items())}


def mechanics_view(mechanics: SurfaceMechanics) -> dict[str, Any]:
    """The marketer-safe payload for one surface's mechanics projection."""

    return {
        "surface": mechanics.surface_id,
        "dimensions": [dimension_view(d) for d in mechanics.dimensions],
        "coverage": mechanics.coverage(),
        "evidenced_dimension_count": mechanics.evidenced_dimension_count(),
        "dimension_count": len(MECHANICS_DIMENSIONS),
    }
