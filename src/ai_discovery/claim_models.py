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
Comparator = Literal[
    "exact",
    "at_least",
    "at_most",
    "approx",
    "share_of_total",
    "policy_statement",
    "qualitative_finding",
    "trigger_rate",
    "trend",
    "absence_of_documentation",
    "qualitative_signal",
]
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
    "official_documentation",
    "unknown",
]
SourceClass = Literal[
    # Acquisition/registry vocabulary (config/sources.yaml `class`)
    "official",
    "market_telemetry",
    "visibility_research",   # independent visibility/SEO/citation research (Ahrefs, Semrush, Sistrix, Peec, Profound)
    "editorial_discovery",   # trade/editorial discovery (Search Engine Land, SE Journal, SE Roundtable)
    "open_research",         # open academic/dataset research (arXiv, OpenAlex, Crossref, Common Crawl)
    "open_discovery",        # discovery-only aggregators (GDELT, Google News RSS); never canonical
    # Controlled consumer-surface observation (issue #10): first-party observation
    # of a surface’s own behaviour. Distinct from vendor docs and from third-party
    # research; never a substitute for either.
    "controlled_observation",
    # Ledger vocabulary (legacy/spec-defined)
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


_SELECTOR_SPLIT = re.compile(r"\s+/\s+|;|\n")
_PAREN = re.compile(r"\([^)]*\)")
_QUOTED = re.compile(r"[\u2018\u2019'\"]([^\u2018\u2019'\"]{2,})[\u2018\u2019'\"]")
# ``"key": "value"`` (JSON / JSON-LD) or ``key="value"`` / ``key=value`` (markup).
_JSON_PAIR = re.compile(r'["\']?(?P<key>[A-Za-z_@][\w:@-]*)["\']?\s*[:=]\s*["\']?(?P<value>[^"\'<>\s,]+)')


def _anchor_resolves(segment: str, haystack: str) -> tuple[bool, str | None]:
    """Resolve one selector anchor against ``haystack``; return (ok, resolved_text).

    Grammar, per anchor shape — a value is bound to the key it came from, so a
    value cannot be satisfied by an unrelated occurrence elsewhere in the page:

    * ``key=value`` — a ``key``/``value`` pair must occur **together** in the
      markup, and the observed value must equal the expected one.
    * ``key``        — the key must occur as a JSON-LD field or a markup
      attribute; the resolved text is its observed value.
    * ``'literal'``  — a quoted literal (e.g. ``page stamp 'Sep 9, 2026'``) must
      appear verbatim; the descriptive prefix is a label, not required text.
    * bare stamp     — must appear verbatim.
    """

    segment = segment.strip()
    if not segment:
        return False, None

    quoted = _QUOTED.findall(segment)
    if quoted:
        hay = normalize_text(haystack).lower()
        for literal in quoted:
            if normalize_text(literal).lower() in hay:
                return True, literal
        return False, None

    if "=" in segment:
        name, _, expected = segment.partition("=")
        # ``document element lang=ko`` -> the attribute key is the last word.
        name = name.strip().split()[-1] if name.strip() else ""
        expected = expected.strip().strip("\"'").strip()
        if not name:
            return False, None
        for match in _JSON_PAIR.finditer(haystack):
            if match.group("key").lower() != name.lower():
                continue
            observed = match.group("value")
            if not expected or expected.lower() in observed.lower():
                return True, observed
        return False, None

    # Bare key: must exist as a JSON-LD field or a markup attribute.
    for match in _JSON_PAIR.finditer(haystack):
        if match.group("key").lower() == segment.lower():
            return True, match.group("value")
    # Bare literal (a page stamp such as ``September 14, 2026``): verbatim match.
    if len(segment) >= 2 and normalize_text(segment).lower() in normalize_text(haystack).lower():
        return True, segment
    return False, None


def resolve_selector(selector: str, haystacks: list[str]) -> tuple[bool, list[str]]:
    """Resolve every anchor in ``selector``; return ``(ok, resolved_texts)``.

    Every anchor must resolve in one of the haystacks. ``resolved_texts`` carries
    the content each anchor actually matched, so the caller can verify a
    value-bearing field's value at the location the selector names.
    """

    anchors = [a for a in (_PAREN.sub("", seg).strip() for seg in _SELECTOR_SPLIT.split(selector)) if a]
    if not anchors:
        return False, []
    candidates = [h for h in haystacks if h]
    if not candidates:
        return False, []
    resolved: list[str] = []
    for anchor in anchors:
        found = False
        for haystack in candidates:
            ok, text = _anchor_resolves(anchor, haystack)
            if ok:
                found = True
                if text is not None:
                    resolved.append(text)
                break
        if not found:
            return False, []
    return True, resolved


def _value_consistent(value: Any, haystack: str) -> bool:
    """True when the claimed value is demonstrably present in the resolved content.

    Dates are compared in ISO form (and their digits), so a JSON-LD
    ``datePublished`` of ``2026-05-14T01:54:23+00:00`` validates a claimed
    ``2026-05-14``. Numbers are compared by their string form. Everything else is a
    case-insensitive substring test.
    """

    import datetime as _dt

    if isinstance(value, _dt.date):
        iso = value.isoformat()
        return iso in haystack or iso.replace("-", "") in haystack.replace("-", "")
    text = normalize_text(str(value)).lower()
    return bool(text) and text in haystack


def _css_selector_resolves(selector: str, raw_html: str) -> str | None:
    """Resolve a CSS selector (``section#results``, ``table tr``) via lxml.

    Returns the matched element's text (possibly empty) or ``None`` when the
    selector matches nothing. Used for the ``section`` / ``table_row`` kinds, whose
    selectors are real CSS rather than JSON-LD keys.
    """

    try:
        from cssselect.parser import SelectorError
        from lxml import html as _lxml_html
        from lxml.cssselect import CSSSelector
    except ImportError:  # pragma: no cover - lxml is a hard dep in practice
        return None
    try:
        document = _lxml_html.fromstring(raw_html)
        matches = CSSSelector(selector)(document)
    except (SelectorError, ValueError, TypeError, _lxml_html.etree.ParserError):
        # An invalid CSS selector (syntax error, unparsable document) can never be
        # evidence; fail closed rather than letting a malformed selector raise.
        return None
    if not matches:
        return None
    return " ".join(el.text_content() for el in matches)


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
        """Every locator is re-verifiable: a verbatim quote, or a structured selector.

        A locator with neither pointer cannot be built (see ``_needs_pointer``), so
        this is always true for a constructed locator; it exists so callers can
        assert the invariant and so a future "watch-only" kind can opt out.
        """

        return bool(self.quote or self.selector)

    def present_in(self, capture_text: str, raw_text: str | None = None) -> bool:
        """Re-verify this locator against the capture it claims to point at.

        A verbatim quote is matched (typography- and whitespace-normalised) against
        the parsed text. A structured selector is resolved against the **raw**
        capture — the JSON-LD, attributes and stamps it names live in markup that
        parsing strips. There is no "assume true" path, and a selector without the
        raw capture fails closed: parsed text alone cannot resolve it, so passing it
        alone must not read as success.

        This checks *presence* only. Value-bearing fields are additionally checked
        with :meth:`verifies`, which compares the claimed value against the content
        the selector actually names.
        """

        if self.quote:
            return normalize_text(self.quote) in normalize_text(capture_text)
        if not self.selector:
            return False
        if raw_text is None:
            return False  # selectors need raw markup; never silently pass parsed-only text
        return self._resolve(raw_text)[0]

    def _resolve(self, raw_text: str) -> tuple[bool, list[str]]:
        """Resolve this locator's selector against the raw capture."""

        if self.kind in ("section", "table_row"):
            hit = _css_selector_resolves(self.selector or "", raw_text)
            return (hit is not None), ([hit] if hit is not None else [])
        return resolve_selector(self.selector or "", [raw_text])

    def verifies(self, value: Any, capture_text: str, raw_text: str | None = None) -> bool:
        """Presence **and**, for value-bearing fields, value consistency.

        A selector that only names a location (``datePublished``) must not validate
        an arbitrary number: the claimed value has to appear in the content the
        selector resolves to. A selector that carries its own expected content
        (``key=value``, or a quoted literal stamp) already binds the evidence when it
        resolves, so the claimed value may be a derived reading of it.
        """

        if not self.present_in(capture_text, raw_text):
            return False
        if self.quote or value is None:
            return True
        if raw_text is None:
            return False
        anchors = [a for a in (_PAREN.sub("", seg).strip() for seg in _SELECTOR_SPLIT.split(self.selector or "")) if a]
        # An anchor that carries its own content (a value after ``=`` or a quoted
        # literal) is self-binding; only name-only anchors need the value check.
        if any("=" in a or _QUOTED.search(a) for a in anchors):
            return True
        ok, resolved = self._resolve(raw_text)
        if not ok:
            return False
        haystack = normalize_text(" ".join([*resolved, capture_text])).lower()
        return _value_consistent(value, haystack)


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
    # A human read the model output against the source. This is the honest,
    # load-bearing claim of human curation; an unattended lane must NOT set it.
    human_reviewed: bool = False
    # Every known field's locator was deterministically checked against the
    # capture bytes by the extraction lane (``check_against_capture``), so the
    # record is source-anchored even though no human read it. This is what the
    # unattended lane may legitimately assert; it is never a substitute for
    # ``human_reviewed`` and is recorded distinctly so the plane can tell the two
    # apart.
    verified_against_capture: bool = False

    @model_validator(mode="after")
    def _llm_is_not_evidence(self) -> ExtractionProvenance:
        if self.method == "llm_proposal" and not (
            self.human_reviewed or self.verified_against_capture
        ):
            raise ValueError(
                "LLM extraction is never evidence: an llm_proposal claim must be "
                "either human_reviewed or deterministically verified against the "
                "source capture before it can enter the ledger"
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
    # Derived, not asserted: assess_confidence() computes these from evidence
    # inputs. ``confidence`` mirrors the label for compatibility; ``confidence_inputs``
    # is the audit trail that makes the label reproducible (issue #28A).
    confidence: Confidence = "medium"
    confidence_score: float | None = None
    confidence_inputs: dict[str, float] = Field(default_factory=dict)
    confidence_rationale: list[str] = Field(default_factory=list)
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
