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
``unknown``. It also never manufactures assertions from registry metadata: a claim lights a
dimension only through an explicit, auditable mapping (``DIMENSION_TOPICS``) or a
content-gated signal (``CLAIM_SIGNALS``); a share-only claim lights nothing.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
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
    # Only topics that *inherently* assert a mechanic appear here. A coarse
    # topic that merely *might* relate (citations, commerce, optimisation) is
    # deliberately absent: it lights a dimension only through the explicit,
    # content-gated CLAIM_SIGNALS below, never by topic alone.
    "search_trigger": ("retrieval_index",),
    "retrieval_provider": ("retrieval_index",),
    "query_rewrite": ("retrieval_index",),
    "crawling_indexing_controls": ("crawler_index_policy",),
    "freshness_recrawl": ("crawler_index_policy",),
    "candidate_selection_reranking": (),
    "citation_presentation": (),
    "shopping_product_feed": (),
    "local_retrieval": (),
    "social_community_retrieval": (),
    "mode_region_differences": (),
    "answer_type": (),
    "marketer_controllable_inputs": (),
}

#: Content-gated signals: a (topic, regex) pair that must ALL match a claim's
#: own statement or metric text before the topic may light the dimension. This is
#: the "claim-level gating" issue #56 review F1 asked for: a market-share claim
#: about citations must not light ``citation_presentation``; only a claim whose
#: text actually asserts a presentation/feed/eligibility mechanic may.
#:
#: Deterministic and auditable by design — every gate is a stated pattern, and a
#: new gate is a reviewed edit here, never a model judgement at request time.
CLAIM_SIGNALS: dict[str, tuple[tuple[str, str], ...]] = {
    "candidate_selection_reranking": (
        (
            "retrieval_index",
            r"\b(rank|rerank|re-rank|select|selection|prioriti[sz]|order(?:ing)?)\b",
        ),
        (
            "citations_sources",
            r"\b(rank|rerank|re-rank|select|selection|prioriti[sz]|order(?:ing)?)\b",
        ),
    ),
    "citation_presentation": (
        (
            "citations_sources",
            (
                r"\b(inline|footer|footnote|card|link(?:s|ed|ing)?|embed(?:s|ded|ding)?|attribut(?:e|ed|ion)|"
                r"cite(?:s|d)? per|citations? per|sources? per|display(?:ed|s)?|present(?:ed|ation)|reference(?:s|d)?)\b"
            ),
        ),
    ),
    "shopping_product_feed": (
        (
            "commerce_ads",
            (
                r"\b(product|products|feed|feeds|catalog(?:ue)?|shopping|merchant|carousel|sponsored|"
                r"product listing|store|retailer|price|availability|checkout)\b"
            ),
        ),
    ),
    # Social/local need *sourcing* language, not merely a domain mention: a
    # "Reddit citation share" number is a share claim, not a stated mechanic.
    "local_retrieval": (
        (
            "retrieval_index",
            (
                r"\b(?:source[sd]? (?:from|via)|retriev\w* (?:from|via)|draws? (?:on|from)|uses?)\b"
                r"[^.]{0,40}\b(?:local|maps?|places?|near me|geo(?:graphic)?)\b"
            ),
        ),
        (
            "citations_sources",
            (
                r"\b(?:source[sd]? (?:from|via)|retriev\w* (?:from|via)|draws? (?:on|from)|uses?)\b"
                r"[^.]{0,40}\b(?:local|maps?|places?|near me|geo(?:graphic)?)\b"
            ),
        ),
    ),
    "social_community_retrieval": (
        (
            "citations_sources",
            (
                r"\b(?:source[sd]? (?:from|via)|retriev\w* (?:from|via)|draws? (?:on|from)|uses?|"
                r"grounded (?:in|on)|pulls? from)\b[^.]{0,40}"
                r"\b(?:reddit|forum|forums|community|communities|quora|stack ?exchange|user-generated)\b"
            ),
        ),
        (
            "retrieval_index",
            (
                r"\b(?:source[sd]? (?:from|via)|retriev\w* (?:from|via)|draws? (?:on|from)|uses?|"
                r"grounded (?:in|on))\b[^.]{0,40}\b(?:reddit|forum|community|communities|quora|social)\b"
            ),
        ),
    ),
    "answer_type": (
        ("retrieval_index", r"\b(grounded|retriev|generat(?:e|ed|ive)|direct answer|synthes|compose(?:d|s)?)\b"),
        ("citations_sources", r"\b(grounded|retriev|direct answer|synthes|compose(?:d|s)?)\b"),
    ),
    "marketer_controllable_inputs": (
        (
            "crawler_index_policy",
            (
                r"\b(robots\.txt|sitemap|llms\.txt|user-agent|user agent|noindex|allow(?:ed)?|disallow|"
                r"crawl(?:ing)? (?:delay|budget)|markup|structured data|schema)\b"
            ),
        ),
        (
            "commerce_ads",
            (
                r"\b(feed|product listing|merchant|markup|structured data|schema|catalog(?:ue)?)\b"
            ),
        ),
        (
            "optimisation_implication",
            (
                r"\b(robots\.txt|sitemap|llms\.txt|markup|structured data|schema|feed|eligib)\b"
            ),
        ),
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
    #: Why the confidence is what it is, copied verbatim from the evidence-derived
    #: confidence rationale (issue #58: "a one-line why this confidence"). A
    #: marketer can read the reason without learning the confidence model.
    confidence_rationale: tuple[str, ...] = ()
    #: Freshness of the capture the claim rests on, as an explicit state. Never a
    #: guess: an absent timestamp is ``unknown``.
    freshness_state: str = "unknown"
    freshness_age_days: int | None = None
    measurement_mode: str | None = None
    methodology_notes: str | None = None
    limitations: tuple[str, ...] = ()
    #: Scope the evidence applies to, so a mode/region-specific fact is not
    #: silently generalised to the whole surface.
    modes: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    relates_to_claim_id: str | None = None
    relationship: str = "new"
    #: The surface value as the claim stored it, plus the canonical registry id
    #: it resolved to — so surface attribution from an alias stays auditable
    #: end-to-end (issue #56 review F4).
    claimed_surface_value: str | None = None
    canonical_surface_id: str | None = None
    #: Which methodology fields were asserted by the claim vs defaulted. A null
    #: methodology field is NOT "verified absent" — it is unstated (review F5).
    methodology_completeness: str = "unknown"

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


def _freshness_of(observed: dt.datetime | None) -> dict[str, Any]:
    """Capture freshness as an explicit state, mirroring the observations read model.

    Kept here (not imported) so the mechanics contract has one owner for its own
    payload shape; the thresholds match ``observations._freshness`` exactly.
    """

    if observed is None:
        return {"state": "unknown", "age_days": None}
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=dt.UTC)
    age = (dt.datetime.now(dt.UTC) - observed).days
    if age <= 7:
        state = "fresh"
    elif age <= 45:
        state = "recent"
    elif age <= 180:
        state = "aging"
    else:
        state = "stale"
    return {"state": state, "age_days": age}


def _methodology_completeness(methodology: dict[str, Any]) -> str:
    """How much methodology the claim actually states (never read null as absent)."""

    stated = sum(
        1
        for f in ("measurement_mode", "metric_family", "denominator", "sample_size",
                  "unit_of_analysis", "time_window", "geography")
        if methodology.get(f)
    )
    if stated == 0:
        return "not_stated"
    if stated <= 2:
        return "sparse"
    return "detailed"


def _evidence_from_claim(row: dict[str, Any], canonical_scope: str | None = None) -> MechanicsEvidence | None:
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

    rationale = tuple((row.get("confidence_detail") or {}).get("rationale") or ())
    fresh = _freshness_of(parsed_observed)
    raw_surfaces = list(row.get("surfaces") or [])
    return MechanicsEvidence(
        confidence_rationale=rationale,
        freshness_state=fresh["state"],
        freshness_age_days=fresh["age_days"],
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
        claimed_surface_value=raw_surfaces[0] if raw_surfaces else None,
        canonical_surface_id=canonical_scope,
        methodology_completeness=_methodology_completeness(methodology),
    )


import re as _re  # local alias: keeps the module's public surface clean

_SIGNAL_CACHE: dict[tuple[str, str], _re.Pattern[str]] = {}


def _signal_regex(topic: str, pattern: str) -> _re.Pattern[str]:
    key = (topic, pattern)
    cached = _SIGNAL_CACHE.get(key)
    if cached is None:
        cached = _re.compile(pattern, _re.IGNORECASE)
        _SIGNAL_CACHE[key] = cached
    return cached


def _claim_text(row: dict[str, Any]) -> str:
    """The claim's own searchable text: statement plus every metric value/label."""

    parts = [row.get("statement") or ""]
    for m in row.get("metrics") or []:
        parts.append(str(m.get("label") or ""))
        parts.append(str(m.get("value_text") or ""))
        parts.append(str(m.get("unit") or ""))
        parts.append(str(m.get("definition") or ""))
    return " ".join(parts)


def _claim_lights_dimension(row: dict[str, Any], dimension: str) -> bool:
    """True only when a claim genuinely asserts this mechanics dimension.

    Two independent gates, both deterministic:

    1. **Inherent topic** (``DIMENSION_TOPICS``): the topic *is* the mechanic
       (e.g. a ``retrieval_index`` claim is about retrieval).
    2. **Content-gated signal** (``CLAIM_SIGNALS``): a coarse topic (citations,
       commerce, optimisation) may light the dimension only when the claim's own
       text matches the stated pattern for that (topic, dimension) pair.

    A market-share/citation-share claim therefore never lights
    ``citation_presentation`` unless its text actually asserts a presentation
    mechanic (links, inline, per-response counts, ...). This is the claim-level
    gating that keeps a coarse topic from masquerading as a mechanic.
    """

    topic = row.get("topic")
    if topic in DIMENSION_TOPICS.get(dimension, ()):
        return True
    text = _claim_text(row)
    for sig_topic, pattern in CLAIM_SIGNALS.get(dimension, ()):
        if topic == sig_topic and _signal_regex(sig_topic, pattern).search(text):
            return True
    return False


def _claims_for(
    claims: list[dict[str, Any]],
    surface_id: str,
    dimension: str,
) -> list[dict[str, Any]]:
    """Real claims that (a) name this surface and (b) genuinely assert this dimension."""

    from .registry import resolve_surface_id

    out: list[dict[str, Any]] = []
    for row in claims:
        # Resolve the claim's surface value to a canonical id (read-time only;
        # the stored claim is never rewritten). An unaliased value that is not a
        # real surface never attaches.
        row_surfaces = {resolve_surface_id(s) for s in (row.get("surfaces") or [])}
        if surface_id not in row_surfaces:
            continue
        if _claim_lights_dimension(row, dimension):
            out.append(row)
    return out


def _assertion_from_claims(
    rows: list[dict[str, Any]],
    *,
    surface_id: str,
) -> MechanicsAssertion | None:
    """One evidenced assertion from one or more claims sharing a dimension.

    When two or more claims carry an explicit ``contradicts``/``supersedes``
    relationship (or a claim is marked ``contested``), the dimension is
    ``conflicting``; otherwise evidence is ``known`` unless a claim is marked
    ``watch``, in which case it is ``partially_known``.
    """

    evidences: list[MechanicsEvidence] = []
    for row in rows:
        ev = _evidence_from_claim(row, canonical_scope=surface_id)
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
        assertion = _assertion_from_claims(rows, surface_id=surface_id)
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


def dimension_view(
    state: DimensionState, reconciliation: dict[str, list[dict]] | None = None
) -> dict[str, Any]:
    """The marketer-safe view of one mechanics dimension.

    ``reconciliation`` is the read-only index from
    :func:`ai_discovery.reconciliation.reconciliation_index`. When present, each
    evidence entry carries the persisted reconciliation records that name its
    claim, so a conflict renders *inline* without reimplementing reconciliation in
    React (issue #58). The backend decision is shown verbatim; the UI only joins.
    """

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
                        "confidence_rationale": list(e.confidence_rationale),
                        "freshness_state": e.freshness_state,
                        "freshness_age_days": e.freshness_age_days,
                        "measurement_mode": e.measurement_mode,
                        "methodology_notes": e.methodology_notes,
                        "limitations": list(e.limitations),
                        "modes": list(e.modes),
                        "regions": list(e.regions),
                        "relates_to_claim_id": e.relates_to_claim_id,
                        "relationship": e.relationship,
                        "claimed_surface_value": e.claimed_surface_value,
                        "canonical_surface_id": e.canonical_surface_id,
                        "methodology_completeness": e.methodology_completeness,
                        "reconciliation": (reconciliation or {}).get(e.claim_id, []),
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


def mechanics_view(
    mechanics: SurfaceMechanics, reconciliation: dict[str, list[dict]] | None = None
) -> dict[str, Any]:
    """The marketer-safe payload for one surface's mechanics projection."""

    return {
        "surface": mechanics.surface_id,
        "dimensions": [dimension_view(d, reconciliation) for d in mechanics.dimensions],
        "coverage": mechanics.coverage(),
        "evidenced_dimension_count": mechanics.evidenced_dimension_count(),
        "dimension_count": len(MECHANICS_DIMENSIONS),
    }


# --------------------------------------------------------------------------- #
# Projection cache (issue #56 review F3/D1/D2)
# --------------------------------------------------------------------------- #
#
# The endpoints project ledger claims on each request. The projection is a pure
# function of (surface ids, ledger claims), so it is cached in-process.
#
# Invalidation is *bounded*, and stated honestly: the token is the claim count
# plus the newest ``observed_at``. That changes on the append-only writes this
# ledger actually performs (a new or superseding claim). It does NOT detect an
# in-place UPDATE of an existing claim (a data correction) — for that the TTL is
# the bound. Worst-case staleness after an in-place correction is therefore the
# TTL, not zero; do not read the cache as "never stale".
#
# The cache is keyed by the surface-ids signature *and* the token, so a
# single-surface request and a bulk request never thrash one another.

import threading as _threading
import time as _time

_CACHE_LOCK = _threading.Lock()
#: key -> (token, projection, built_at). Bounded: at most one entry per distinct
#: surface-ids signature actually requested (bulk = 1, plus one per single surface).
_CACHE: dict[str, tuple[str, Any, float]] = {}
_CACHE_TTL_SECONDS = 300.0


def ledger_token(claims: list[dict[str, Any]]) -> str:
    """A cheap change token: claim count + newest observed_at.

    Detects append-only writes (new / superseding claims). It does NOT detect an
    in-place claim edit, which the TTL bounds instead.
    """

    newest = ""
    for row in claims:
        observed = (row.get("dates") or {}).get("observed_at") or ""
        newest = max(newest, observed)
    return f"{len(claims)}|{newest}"


def _cached(key: str, token: str, build: Callable[[], Any], *, now: float | None) -> Any:
    clock = now if now is not None else _time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is not None and entry[0] == token and (clock - entry[2]) < _CACHE_TTL_SECONDS:
            return entry[1]
    value = build()
    with _CACHE_LOCK:
        _CACHE[key] = (token, value, clock)
    return value


def cached_project_all(
    surface_ids: list[str],
    claims: list[dict[str, Any]],
    *,
    now: float | None = None,
) -> dict[str, SurfaceMechanics]:
    """``project_all`` with an in-process cache keyed by shape + ledger token."""

    sign = ",".join(surface_ids)
    token = ledger_token(claims)
    return _cached(f"all:{sign}", token, lambda: project_all(surface_ids, claims), now=now)


def cached_project_surface(
    surface_id: str,
    claims: list[dict[str, Any]],
    *,
    now: float | None = None,
) -> SurfaceMechanics:
    """``project_surface`` for one surface, cached so a repeat request is free.

    A single surface is projected, never all 35; the cache key includes the
    surface id so single-surface and bulk shapes never collide.
    """

    token = ledger_token(claims)
    return _cached(
        f"one:{surface_id}", token, lambda: project_surface(surface_id, claims), now=now
    )


def clear_projection_cache() -> None:
    """Drop the cache (tests; and an operator escape hatch)."""

    with _CACHE_LOCK:
        _CACHE.clear()
