"""Domain models for the atomic evidence/claim ledger (issue #3).

Rules enforced by validators here rather than by convention:

1. A known field must carry an exact source locator (verbatim quote or
   structured selector); an unknown field must carry none. "Unknown" is a
   first-class value, never a placeholder number.
2. Published, modified, measured and observed (capture) dates are four distinct
   fields and cannot be collapsed into one "date".
3. LLM extraction is never evidence: an ``llm_proposal`` record is rejected
   before it can enter the ledger unless a human reviewed it against the source.
4. The claim id is derived from (source, topic, statement), so the same
   assertion re-extracted from the same source is the same claim.

Every extracted field is traceable because ``iter_provenanced`` walks the whole
model and yields ``(dotted.path -> Provenanced)``; ``claims.py`` writes those
paths to ``claim_locator`` rows.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EXTRACTION_VERSION = "claim-extraction-0.1.0"

ClaimTopic = Literal[
    "audience_usage",
    "retrieval_index",
    "citations_sources",
    "crawler_index_policy",
    "referrals_conversion",
    "commerce_ads",
    "measurement",
    "optimisation_implication",
]
CLAIM_TOPICS: tuple[str, ...] = (
    "audience_usage",
    "retrieval_index",
    "citations_sources",
    "crawler_index_policy",
    "referrals_conversion",
    "commerce_ads",
    "measurement",
    "optimisation_implication",
)

LocatorKind = Literal["verbatim_quote", "jsonld_field", "table_row", "page_stamp", "section"]
ClaimStatus = Literal["current", "contested", "historical", "watch", "unknown"]
Relationship = Literal["new", "supports", "updates", "contradicts", "supersedes", "contextualizes"]
Comparator = Literal["exact", "at_least", "at_most", "approx", "share_of_total"]
Confidence = Literal["high", "medium", "low", "unknown"]
ScopeBasis = Literal["source_stated", "publisher_scope", "inferred", "not_stated"]
MeasurementMode = Literal[
    "vendor_estimate",
    "vendor_panel",
    "consent_panel",
    "clickstream",
    "server_logs",
    "survey",
    "press_release",
    "unknown",
]
SourceClass = Literal[
    "vendor_research",
    "vendor_blog",
    "press_release",
    "news",
    "industry_report",
    "other",
]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_WS = re.compile(r"\s+")
# Typographic characters appear on publisher pages; normalise so a verbatim
# quote check is about the words, not the glyphs.
_GLYPHS = {
    "\u2019": "'",
    "\u2018": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\xa0": " ",
}


def normalize_text(text: str) -> str:
    """Collapse whitespace and normalise publisher typography."""

    for src, dst in _GLYPHS.items():
        text = text.replace(src, dst)
    return _WS.sub(" ", text).strip()


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def claim_id_for(source_id: str, topic: str, statement: str) -> str:
    """Stable 32-hex claim id: sha256(source|topic|statement)[:32]."""

    payload = f"{source_id}|{topic}|{normalize_text(statement)}".encode()
    return hashlib.sha256(payload).hexdigest()[:32]


class Locator(BaseModel):
    """An exact pointer into a capture: a verbatim quote, or a structured selector."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: LocatorKind
    quote: str | None = None
    selector: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _needs_pointer(self) -> Locator:
        if not (self.quote or self.selector):
            raise ValueError("locator requires a verbatim quote or a structured selector")
        return self

    @property
    def checkable(self) -> bool:
        """Quote locators can be re-verified against a fresh capture."""

        return bool(self.quote)

    def present_in(self, capture_text: str) -> bool:
        if not self.quote:
            return True  # structured selectors are re-checked by the selector's owner
        return normalize_text(self.quote) in normalize_text(capture_text)


class Provenanced[T](BaseModel):
    """A field value plus the exact locator that supports it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: T | None = None
    locator: Locator | None = None

    @property
    def known(self) -> bool:
        return self.value is not None

    @model_validator(mode="after")
    def _traceable(self) -> Provenanced[T]:
        if self.value is None and self.locator is not None:
            raise ValueError("an unknown value must not carry a locator")
        if self.value is not None and self.locator is None:
            raise ValueError("a known value requires an exact source locator")
        return self


def unknown() -> Provenanced[Any]:
    """Explicit unknown field: no value, no locator, nothing invented."""

    return Provenanced()


def _field[T](
    value: T | None,
    *,
    quote: str | None = None,
    selector: str | None = None,
    kind: LocatorKind = "verbatim_quote",
    note: str | None = None,
) -> Provenanced[T]:
    """Build a Provenanced field; ``value=None`` yields an explicit unknown."""

    if value is None:
        return Provenanced[T]()
    return Provenanced[T](
        value=value, locator=Locator(kind=kind, quote=quote, selector=selector, note=note)
    )


class Metric(BaseModel):
    """One numeric/typed observation, with its own definition and window."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_id: str
    label: str
    definition: Provenanced[str]
    value: Provenanced[float | str]
    unit: Provenanced[str]
    comparator: Comparator = "exact"
    window: Provenanced[str]
    scope: Provenanced[str]


class DateProfile(BaseModel):
    """Four distinct dates. Conflating them is a schema error, not a style choice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    published_at: Provenanced[dt.date] = Field(default_factory=lambda: Provenanced[dt.date]())
    modified_at: Provenanced[dt.date] = Field(default_factory=lambda: Provenanced[dt.date]())
    measured_window: Provenanced[str] = Field(default_factory=lambda: Provenanced[str]())
    observed_at: dt.datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _ordered(self) -> DateProfile:
        pub, mod = self.published_at.value, self.modified_at.value
        if pub and mod and mod < pub:
            raise ValueError("modified_at cannot precede published_at")
        observed = self.observed_at
        if observed.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if pub and observed.date() < pub:
            raise ValueError("a capture cannot predate the source's publication date")
        return self


class CaptureEvidence(BaseModel):
    """Where the bytes came from. Raw snapshots stay private; only hashes ship."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    publisher: str
    url: str
    canonical_url: str
    source_class: SourceClass
    capture_hash: str  # sha256 of the extracted text actually parsed
    raw_sha256: str | None = None  # sha256 of the fetched bytes
    snapshot_path: str | None = None  # private, hash-addressed
    http_status: int | None = None
    content_type: str | None = None
    text_chars: int | None = None
    robots_allowed: bool | None = None
    fetched_at: dt.datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _hashes(self) -> CaptureEvidence:
        for name in ("capture_hash", "raw_sha256"):
            value = getattr(self, name)
            if value is not None and not _HEX64.match(value):
                raise ValueError(f"{name} must be a lowercase sha256 hex digest")
        return self


class ExtractionProvenance(BaseModel):
    """How the claim was produced. Deterministic parsers are the default."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    method: Literal["deterministic_parser", "llm_proposal"]
    tool: str
    version: str
    rule_id: str | None = None
    human_reviewed: bool = False

    @model_validator(mode="after")
    def _llm_is_not_evidence(self) -> ExtractionProvenance:
        if self.method == "llm_proposal" and not self.human_reviewed:
            raise ValueError(
                "LLM extraction is never evidence: an llm_proposal claim needs "
                "human_reviewed=True against the source capture before it can enter the ledger"
            )
        return self


class StudyMethodology(BaseModel):
    """The study context that makes a claim comparable - or incomparable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surfaces: list[str]
    measurement_mode: MeasurementMode
    metric_family: Provenanced[str]
    metric_definition: Provenanced[str]
    denominator: Provenanced[str]
    prompt_universe: Provenanced[str]
    sample_size: Provenanced[int | str]
    unit_of_analysis: Provenanced[str]
    time_window: Provenanced[str]
    geography: Provenanced[str]
    geography_basis: ScopeBasis = "not_stated"
    language: Provenanced[str]
    language_basis: ScopeBasis = "not_stated"
    devices: Provenanced[str]
    limitations: list[str] = Field(default_factory=list)
    methodology_notes: Provenanced[str]

    @model_validator(mode="after")
    def _scope_basis(self) -> StudyMethodology:
        for field, basis in (
            ("geography", self.geography_basis),
            ("language", self.language_basis),
        ):
            if getattr(self, field).known and basis == "not_stated":
                raise ValueError(
                    f"{field} is known, so its basis must be recorded "
                    "(source_stated | publisher_scope | inferred)"
                )
        return self


class ClaimRecord(BaseModel):
    """The atomic unit of the observation plane."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    source_id: str
    topic: ClaimTopic
    statement: str
    surfaces: list[str] = Field(min_length=1)
    metrics: list[Metric] = Field(min_length=1)
    methodology: StudyMethodology
    dates: DateProfile
    evidence: CaptureEvidence
    capture_anchors: list[Locator] = Field(min_length=1)
    extraction: ExtractionProvenance
    status: ClaimStatus = "current"
    relationship: Relationship = "new"
    supersedes_claim_id: str | None = None
    confidence: Confidence = "medium"
    created_at: dt.datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _consistent(self) -> ClaimRecord:
        expected = claim_id_for(self.source_id, self.topic, self.statement)
        if self.claim_id != expected:
            raise ValueError(f"claim_id {self.claim_id!r} != derived {expected!r}")
        if self.evidence.source_id != self.source_id:
            raise ValueError("evidence.source_id must match source_id")
        if self.relationship in {"updates", "supersedes", "contradicts"} and not (
            self.supersedes_claim_id
        ):
            raise ValueError(f"relationship={self.relationship} requires supersedes_claim_id")
        if self.relationship == "new" and self.supersedes_claim_id:
            raise ValueError("a new claim must not supersede anything")
        return self

    def field_locators(self) -> list[tuple[str, Locator]]:
        return [(path, p.locator) for path, p in iter_provenanced(self) if p.locator]


def iter_provenanced(obj: Any, prefix: str = ""):
    """Yield ``(dotted.path, Provenanced)`` for every value-bearing field."""

    if isinstance(obj, Provenanced):
        yield prefix, obj
        return
    if isinstance(obj, BaseModel):
        for name, value in obj:
            if isinstance(value, (Provenanced, BaseModel)) or (
                isinstance(value, (list, tuple))
                and any(isinstance(v, (Provenanced, BaseModel)) for v in value)
            ):
                child = f"{prefix}.{name}" if prefix else name
                yield from iter_provenanced(value, child)
        return
    if isinstance(obj, (list, tuple)):
        for index, item in enumerate(obj):
            if isinstance(item, (Provenanced, BaseModel)):
                yield from iter_provenanced(item, f"{prefix}[{index}]")
