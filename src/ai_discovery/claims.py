"""Evidence-bound claim extraction and the claim-ledger repository (issue #3).

Test coverage: tests/test_claim_models.py, tests/test_claims.py, tests/test_parser_fidelity.py.

Two responsibilities, both deterministic:

* **Extraction** - ``extract_claim`` turns a *spec* into a :class:`ClaimRecord`.
  A spec declares, for every known field, the exact source quote (or structured
  selector) that supports it. The rule re-normalises both the quote and the
  capture text and refuses to emit a claim when any quote is absent from the
  capture. So a claim can never be produced whose fields are not traceable, and
  a fabricated number cannot survive the check. Prose inference is out of scope
  here; when prose extraction is added it must arrive as an
  ``llm_proposal`` record (see ``ExtractionProvenance``) that a human has
  reviewed against the capture, because LLM output is never evidence.

* **Persistence** - append-only SQLAlchemy ledger tables (``study``, ``claim``,
  ``claim_metric``, ``claim_locator``, ``claim_evidence``). A claim's prose or
  methodology is never updated in place: a new capture writes a new
  ``claim_evidence`` row and a superseding claim gets its own ``claim_id``.

The ledger tables live on the shared declarative ``Base`` from
``ai_discovery.models`` (owned by issue #2). Before that module lands, this file
falls back to a local ``Base`` so the ledger can be unit-tested standalone; the
fallback disappears at integration and the Postgres DDL stays the same.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .claim_models import (
    CLAIM_TOPICS,
    EXTRACTION_VERSION,
    CaptureEvidence,
    ClaimRecord,
    DateProfile,
    ExtractionProvenance,
    Locator,
    Metric,
    Provenanced,
    StudyMethodology,
    claim_id_for,
    normalize_text,
    unknown,
)

try:  # pragma: no cover - presence depends on whether issue #2 has landed
    from .models import Base  # issue #2 provides the shared declarative Base
except ImportError:  # standalone worktree before #2 is merged
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        """Fallback Base so the ledger is testable before #2 lands."""


# --------------------------------------------------------------------------- #
# SQLAlchemy ledger tables
# --------------------------------------------------------------------------- #

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    Mapped,
    Session,  # noqa: F401
    mapped_column,
    sessionmaker,
)

# aliased: ``Claim.relationship`` is a mapped column and would shadow this helper
# inside the class body.
from sqlalchemy.orm import relationship as sa_relationship


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Study(Base):
    """Methodology capture: the context that makes a claim comparable."""

    __tablename__ = "study"

    study_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    publisher: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, index=True)
    source_class: Mapped[str] = mapped_column(String(60))
    title: Mapped[str | None] = mapped_column(Text)
    measurement_mode: Mapped[str] = mapped_column(String(40))
    metric_family: Mapped[str | None] = mapped_column(String(120))
    denominator: Mapped[str | None] = mapped_column(Text)
    prompt_universe: Mapped[str | None] = mapped_column(Text)
    sample_size: Mapped[str | None] = mapped_column(Text)  # NULL == unknown
    unit_of_analysis: Mapped[str | None] = mapped_column(Text)
    time_window: Mapped[str | None] = mapped_column(Text)
    geography: Mapped[str | None] = mapped_column(String(60))
    geography_basis: Mapped[str] = mapped_column(String(30), default="not_stated")
    language: Mapped[str | None] = mapped_column(String(30))
    language_basis: Mapped[str] = mapped_column(String(30), default="not_stated")
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    methodology_notes: Mapped[str | None] = mapped_column(Text)
    extraction_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    claims: Mapped[list[Claim]] = sa_relationship(back_populates="study")


class Claim(Base):
    """The atomic, typed assertion shown in the observation plane."""

    __tablename__ = "claim"

    claim_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    study_id: Mapped[str] = mapped_column(ForeignKey("study.study_id"), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    topic: Mapped[str] = mapped_column(String(40), index=True)
    statement: Mapped[str] = mapped_column(Text)
    surfaces: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="current", index=True)
    relationship: Mapped[str] = mapped_column(String(30), default="new")
    supersedes_claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("claim.claim_id"), nullable=True
    )
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    # Derived-confidence audit trail (issue #28A): the exact scorer inputs and the
    # rationale, so the label can be recomputed and explained without the model.
    confidence_score: Mapped[float | None] = mapped_column(Float)
    confidence_inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_rationale: Mapped[list] = mapped_column(JSON, default=list)
    extraction_method: Mapped[str] = mapped_column(String(30))
    extraction_tool: Mapped[str] = mapped_column(String(80))
    extraction_version: Mapped[str] = mapped_column(String(40))
    rule_id: Mapped[str | None] = mapped_column(String(80))
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_against_capture: Mapped[bool] = mapped_column(Boolean, default=False)

    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    published_at_source: Mapped[str | None] = mapped_column(String(30))
    modified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    measured_window: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    study: Mapped[Study] = sa_relationship(back_populates="claims")
    metrics: Mapped[list[ClaimMetric]] = sa_relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimMetric.metric_id"
    )
    locators: Mapped[list[ClaimLocator]] = sa_relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimLocator.id"
    )
    captures: Mapped[list[ClaimEvidence]] = sa_relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="ClaimEvidence.id"
    )


class ClaimMetric(Base):
    """One typed metric under a claim, with its own definition and window."""

    __tablename__ = "claim_metric"
    __table_args__ = (UniqueConstraint("claim_id", "metric_id", name="uq_claim_metric"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claim.claim_id", ondelete="CASCADE"), index=True
    )
    metric_id: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(160))
    comparator: Mapped[str] = mapped_column(String(20), default="exact")
    definition: Mapped[str] = mapped_column(Text)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_number: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    window: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)

    claim: Mapped[Claim] = sa_relationship(back_populates="metrics")


class ClaimLocator(Base):
    """Exact evidence pointer for one field path of one claim."""

    __tablename__ = "claim_locator"
    __table_args__ = (UniqueConstraint("claim_id", "field_path", name="uq_claim_locator_field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claim.claim_id", ondelete="CASCADE"), index=True
    )
    field_path: Mapped[str] = mapped_column(String(200))
    locator_kind: Mapped[str] = mapped_column(String(30))
    quote: Mapped[str | None] = mapped_column(Text)
    selector: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    claim: Mapped[Claim] = sa_relationship(back_populates="locators")


class ClaimEvidence(Base):
    """Append-only link from a claim to a capture. Never updated in place.

    ``evidence_id`` is a soft reference to ``evidence_item.id`` (issue #2). It is
    promoted to a real foreign key by the integration migration once the
    evidence table exists, so this row set stays insert-only either way.
    """

    __tablename__ = "claim_evidence"
    __table_args__ = (UniqueConstraint("claim_id", "capture_hash", name="uq_claim_capture"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(
        ForeignKey("claim.claim_id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, index=True)
    capture_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_sha256: Mapped[str | None] = mapped_column(String(64))
    snapshot_path: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    claim: Mapped[Claim] = sa_relationship(back_populates="captures")


class ChangeEventRow(Base):
    """Persisted change event (issue #23). Append-only; payload is the event JSON."""

    __tablename__ = "change_event"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(Text)
    surfaces: Mapped[list[str]] = mapped_column(JSON, default=list)
    dedupe_key: Mapped[str | None] = mapped_column(String(200), index=True)
    payload: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class BriefSnapshotRow(Base):
    """One generated weekly brief, persisted so the product reads real output."""

    __tablename__ = "brief_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    payload: Mapped[str] = mapped_column(Text)


LEDGER_TABLES = (
    Study.__table__,
    Claim.__table__,
    ClaimMetric.__table__,
    ClaimLocator.__table__,
    ClaimEvidence.__table__,
    ChangeEventRow.__table__,
    BriefSnapshotRow.__table__,
)


# --------------------------------------------------------------------------- #
# Spec -> ClaimRecord extraction
# --------------------------------------------------------------------------- #


class ClaimSpecError(ValueError):
    """Raised when a spec is malformed or a quote is absent from the capture."""


class Capture:
    """A local capture under extraction: raw bytes plus the text actually parsed."""

    def __init__(self, *, raw: bytes, text: str, fetched_at: dt.datetime | None = None):
        self.raw = raw
        self.text = text
        self.fetched_at = fetched_at or _utcnow()

    @property
    def raw_text(self) -> str:
        """The raw capture as text.

        Structured selectors (``jsonld_field`` / ``table_row`` / ``section`` /
        ``page_stamp``) name markup that ``text`` has had stripped, so they are
        resolved against this. Undecodable bytes are replaced rather than raising,
        because a locator check must never be the thing that crashes extraction.
        """

        return self.raw.decode("utf-8", errors="replace")

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def capture_hash(self) -> str:
        """sha256 of the normalised text, mirroring EvidenceItem.capture_hash."""

        return hashlib.sha256(normalize_text(self.text).encode()).hexdigest()

    @property
    def text_chars(self) -> int:
        return len(self.text)


def extract_capture_text(raw_html: str) -> str:
    """Deterministic HTML -> text: drop scripts/styles, unescape, collapse space."""

    import html as _html

    text = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = _html.unescape(text)
    return normalize_text(text)


def _date(value: Any, selector: str | None, *, kind: str = "jsonld_field") -> Provenanced[dt.date]:
    """A dated value must name where the date came from; otherwise it stays unknown."""

    if value is None:
        return Provenanced[dt.date]()
    if not selector:
        raise ClaimSpecError(
            f"date {value!r} needs a selector (which heading/meta/JSON-LD field it came from)"
        )
    return Provenanced[dt.date](
        value=dt.date.fromisoformat(str(value)), locator=Locator(kind=kind, selector=selector)
    )


def _field_from_spec(raw: Any, default_kind: str = "verbatim_quote") -> Provenanced[Any]:
    """Read a spec field: ``null`` -> unknown; ``{"value": x, "quote"|"selector": y}`` -> known."""

    if raw is None:
        return Provenanced()
    if not isinstance(raw, Mapping):
        raise ClaimSpecError(f"field spec must be null or an object, got {raw!r}")
    if "value" not in raw:
        raise ClaimSpecError(f"field spec missing 'value': {raw!r}")
    return Provenanced(
        value=raw["value"],
        locator=Locator(
            kind=raw.get("kind", default_kind),
            quote=raw.get("quote"),
            selector=raw.get("selector"),
            note=raw.get("note"),
        ),
    )


def extract_claim(
    *,
    spec: Mapping[str, Any],
    capture: Capture,
    rule_id: str | None = None,
) -> ClaimRecord:
    """Build a validated :class:`ClaimRecord`, refusing any unsupported field.

    Raises :class:`ClaimSpecError` when a declared quote is not present verbatim
    in the capture text, or when a value is supplied without a locator.
    """

    source = spec.get("source") or {}
    for key in ("source_id", "publisher", "url", "canonical_url", "source_class"):
        if not source.get(key):
            raise ClaimSpecError(f"source.{key} is required")

    topic = spec.get("topic")
    if topic not in CLAIM_TOPICS:
        raise ClaimSpecError(f"topic must be one of {CLAIM_TOPICS}, got {topic!r}")
    statement = (spec.get("statement") or "").strip()
    if not statement:
        raise ClaimSpecError("statement is required")

    provenance_fields: dict[str, Provenanced[Any]] = {
        "methodology.metric_family": _field_from_spec(
            (spec.get("methodology") or {}).get("metric_family")
        ),
        "methodology.metric_definition": _field_from_spec(
            (spec.get("methodology") or {}).get("metric_definition")
        ),
        "methodology.denominator": _field_from_spec(
            (spec.get("methodology") or {}).get("denominator")
        ),
        "methodology.prompt_universe": _field_from_spec(
            (spec.get("methodology") or {}).get("prompt_universe")
        ),
        "methodology.sample_size": _field_from_spec(
            (spec.get("methodology") or {}).get("sample_size")
        ),
        "methodology.unit_of_analysis": _field_from_spec(
            (spec.get("methodology") or {}).get("unit_of_analysis")
        ),
        "methodology.time_window": _field_from_spec(
            (spec.get("methodology") or {}).get("time_window")
        ),
        "methodology.geography": _field_from_spec((spec.get("methodology") or {}).get("geography")),
        "methodology.language": _field_from_spec((spec.get("methodology") or {}).get("language")),
        "methodology.devices": _field_from_spec((spec.get("methodology") or {}).get("devices")),
        "methodology.methodology_notes": _field_from_spec(
            (spec.get("methodology") or {}).get("methodology_notes")
        ),
    }

    metrics: list[Metric] = []
    for index, raw_metric in enumerate(spec.get("metrics") or []):
        if not isinstance(raw_metric, Mapping):
            raise ClaimSpecError(f"metrics[{index}] must be an object")
        metrics.append(
            Metric(
                metric_id=raw_metric.get("metric_id") or f"m{index + 1}",
                label=raw_metric.get("label") or raw_metric.get("metric_id") or f"m{index + 1}",
                definition=_field_from_spec(raw_metric.get("definition")),
                value=_field_from_spec(raw_metric.get("value")),
                unit=_field_from_spec(raw_metric.get("unit")),
                comparator=raw_metric.get("comparator", "exact"),
                window=_field_from_spec(raw_metric.get("window")),
                scope=_field_from_spec(raw_metric.get("scope")),
            )
        )
        provenanced = metrics[-1]
        for name in ("definition", "value", "unit", "window", "scope"):
            provenance_fields[f"metrics[{index}].{name}"] = getattr(provenanced, name)
    if not metrics:
        raise ClaimSpecError("at least one metric is required")

    dates_raw = spec.get("dates") or {}
    observed_raw = dates_raw.get("observed_at")
    if not observed_raw:
        raise ClaimSpecError(
            "dates.observed_at is required (a claim must record when it was captured)"
        )
    dates = DateProfile(
        published_at=_date(dates_raw.get("published_at"), dates_raw.get("published_at_selector")),
        modified_at=_date(dates_raw.get("modified_at"), dates_raw.get("modified_at_selector")),
        # measured_window and observed_at are handled below
        measured_window=_field_from_spec(dates_raw.get("measured_window")),
        observed_at=dt.datetime.fromisoformat(str(observed_raw)),
    )
    provenance_fields["dates.measured_window"] = dates.measured_window

    anchors = [Locator(**a) for a in (spec.get("capture_anchors") or [])]
    if not anchors:
        raise ClaimSpecError("capture_anchors must contain at least one locator")

    evidence = CaptureEvidence(
        source_id=source["source_id"],
        publisher=source["publisher"],
        url=source["url"],
        canonical_url=source["canonical_url"],
        source_class=source["source_class"],
        capture_hash=capture.capture_hash,
        raw_sha256=capture.raw_sha256,
        snapshot_path=source.get("snapshot_path"),
        http_status=source.get("http_status"),
        content_type=source.get("content_type"),
        text_chars=capture.text_chars,
        robots_allowed=source.get("robots_allowed"),
        fetched_at=capture.fetched_at,
    )

    extraction_raw = spec.get("extraction") or {}
    extraction = ExtractionProvenance(
        method=extraction_raw.get("method", "deterministic_parser"),
        tool=extraction_raw.get("tool", "ai_discovery.claims"),
        version=extraction_raw.get("version", EXTRACTION_VERSION),
        rule_id=rule_id or extraction_raw.get("rule_id"),
        human_reviewed=bool(extraction_raw.get("human_reviewed", False)),
        verified_against_capture=bool(extraction_raw.get("verified_against_capture", False)),
    )

    methodology_raw = spec.get("methodology") or {}
    methodology = StudyMethodology(
        surfaces=[s for s in (spec.get("surfaces") or []) if s],
        measurement_mode=methodology_raw.get("measurement_mode", "unknown"),
        metric_family=provenance_fields["methodology.metric_family"],
        metric_definition=provenance_fields["methodology.metric_definition"],
        denominator=provenance_fields["methodology.denominator"],
        prompt_universe=provenance_fields["methodology.prompt_universe"],
        sample_size=provenance_fields["methodology.sample_size"],
        unit_of_analysis=provenance_fields["methodology.unit_of_analysis"],
        time_window=provenance_fields["methodology.time_window"],
        geography=provenance_fields["methodology.geography"],
        geography_basis=methodology_raw.get("geography_basis", "not_stated"),
        language=provenance_fields["methodology.language"],
        language_basis=methodology_raw.get("language_basis", "not_stated"),
        devices=provenance_fields["methodology.devices"],
        limitations=[str(x) for x in (methodology_raw.get("limitations") or [])],
        methodology_notes=provenance_fields["methodology.methodology_notes"],
    )
    if not methodology.surfaces:
        raise ClaimSpecError("surfaces must list at least one surface id")

    relationship = spec.get("relationship", "new")
    record = ClaimRecord(
        claim_id=claim_id_for(source["source_id"], topic, statement),
        source_id=source["source_id"],
        topic=topic,
        statement=statement,
        surfaces=methodology.surfaces,
        metrics=metrics,
        methodology=methodology,
        dates=dates,
        evidence=evidence,
        capture_anchors=anchors,
        extraction=extraction,
        status=spec.get("status", "current"),
        relationship=relationship,
        supersedes_claim_id=spec.get("supersedes_claim_id") or None,
    )

    missing = check_against_capture(record, capture)
    if missing:
        joined = "; ".join(missing)
        raise ClaimSpecError(f"declared evidence not found in capture: {joined}")
    return with_derived_confidence(record, spec=spec)


def check_against_capture(record: ClaimRecord, capture: Capture) -> list[str]:
    """Return human-readable failures for every locator not found in the capture.

    Every locator kind is re-verified: a verbatim quote against the parsed text, a
    structured selector against the raw capture (with the parsed text as fallback)
    because the markup it names — JSON-LD, attributes, stamps — is stripped by
    parsing. A selector that does not resolve fails, so a claim cannot pass on a
    locator that points at nothing.
    """

    failures: list[str] = []
    for anchor in record.capture_anchors:
        if not anchor.present_in(capture.text, capture.raw_text):
            failures.append(f"capture_anchors: {anchor.quote or anchor.selector}")
    for path, locator in record.field_locators():
        value = _value_at_path(record, path)
        if not locator.verifies(value, capture.text, capture.raw_text):
            failures.append(f"{path}: {locator.quote or locator.selector}")
    return failures


def _value_at_path(record: ClaimRecord, path: str) -> Any:
    """The claimed value at a dotted ``field_locators()`` path, or ``None``.

    ``field_locators`` walks the model, so a path like ``metrics[0].value`` names
    the provenance entry directly; this returns the value it supports so
    ``Locator.verifies`` can check the value against the resolved content.
    """

    node: Any = record
    for part in path.split("."):
        if "[" in part:
            name, _, index = part.partition("[")
            node = getattr(node, name)
            node = node[int(index.rstrip("]"))]
        else:
            node = getattr(node, part)
    return getattr(node, "value", None)


def with_derived_confidence(
    record: ClaimRecord,
    *,
    spec: Mapping[str, Any] | None = None,
    corroborating_sources: int = 0,
) -> ClaimRecord:
    """Return ``record`` with confidence derived from evidence, not assertion.

    Any ``confidence`` in the spec (a spec-author or, after PR #22, an LLM value)
    is recorded for audit but can never set the label (issue #28A): the label is a
    pure function of the derived inputs, and those inputs are persisted so the
    label can be recomputed and explained.
    """

    from .confidence import assess_confidence

    asserted = None
    if spec is not None and spec.get("confidence") is not None:
        asserted = str(spec["confidence"])
    assessment = assess_confidence(
        record, corroborating_sources=corroborating_sources, model_asserted=asserted
    )
    # Map the 5-level scorer label onto the ledger's 4-level Confidence vocabulary,
    # downgrading (never upgrading) so the stricter of the two is always kept.
    ledger_label = {
        "high": "high",
        "medium_high": "medium",
        "medium": "medium",
        "low": "low",
        "unresolved": "unknown",
    }[assessment.label]
    return record.model_copy(
        update={
            "confidence": ledger_label,
            "confidence_score": assessment.score,
            "confidence_inputs": assessment.inputs,
            "confidence_rationale": assessment.rationale,
        }
    )


RULE_SOURCE_CLASS_DEFAULT = {
    "similarweb_visit_share_v1": "vendor_research",
}


# --------------------------------------------------------------------------- #
# Ledger repository
# --------------------------------------------------------------------------- #


def create_ledger_engine(database_url: str) -> Engine:
    """Engine factory. Postgres is canonical; SQLite is accepted for tests/proof."""

    from sqlalchemy import create_engine

    return create_engine(database_url, future=True)


def init_ledger(engine: Engine) -> None:
    """Create only the ledger tables, leaving issue #2's tables alone."""

    Base.metadata.create_all(engine, tables=list(LEDGER_TABLES))


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _value_text(value: Provenanced[Any]) -> str | None:
    """Persist a provenanced value as text, keeping "unknown" unknown.

    ``str(None)`` is the literal string ``"None"``, which would turn a first-class
    unknown into a value a drill-down renders or a consumer parses (issue #25).
    An unknown value persists as SQL NULL, matching ``value_number``.
    """

    return None if value.value is None else str(value.value)


def persist_claim(engine: Engine, record: ClaimRecord) -> tuple[str, bool]:
    """Insert a study + claim + metrics + locators + capture. Append-only.

    Returns ``(claim_id, created)``. Re-persisting the same claim id inserts a new
    ``claim_evidence`` row (new capture hash) and leaves prior rows untouched.
    """

    session_factory = sessionmaker(bind=engine, future=True)
    with session_factory() as session:
        study_id = hashlib.sha256(
            f"{record.source_id}|{record.evidence.canonical_url}|{record.evidence.capture_hash}".encode()
        ).hexdigest()[:32]
        if session.get(Study, study_id) is None:
            session.add(
                Study(
                    study_id=study_id,
                    source_id=record.source_id,
                    publisher=record.evidence.publisher,
                    url=record.evidence.url,
                    canonical_url=record.evidence.canonical_url,
                    source_class=record.evidence.source_class,
                    measurement_mode=record.methodology.measurement_mode,
                    metric_family=record.methodology.metric_family.value,
                    denominator=record.methodology.denominator.value,
                    prompt_universe=record.methodology.prompt_universe.value,
                    sample_size=None
                    if not record.methodology.sample_size.known
                    else str(record.methodology.sample_size.value),
                    unit_of_analysis=record.methodology.unit_of_analysis.value,
                    time_window=record.methodology.time_window.value,
                    geography=record.methodology.geography.value,
                    geography_basis=record.methodology.geography_basis,
                    language=record.methodology.language.value,
                    language_basis=record.methodology.language_basis,
                    limitations=record.methodology.limitations,
                    methodology_notes=record.methodology.methodology_notes.value,
                    extraction_version=record.extraction.version,
                )
            )
            session.flush()

        created = session.get(Claim, record.claim_id) is None
        if created:
            session.add(
                Claim(
                    claim_id=record.claim_id,
                    study_id=study_id,
                    source_id=record.source_id,
                    topic=record.topic,
                    statement=record.statement,
                    surfaces=record.surfaces,
                    status=record.status,
                    relationship=record.relationship,
                    supersedes_claim_id=record.supersedes_claim_id,
                    confidence=record.confidence,
                    confidence_score=record.confidence_score,
                    confidence_inputs=record.confidence_inputs,
                    confidence_rationale=record.confidence_rationale,
                    extraction_method=record.extraction.method,
                    extraction_tool=record.extraction.tool,
                    extraction_version=record.extraction.version,
                    rule_id=record.extraction.rule_id,
                    human_reviewed=record.extraction.human_reviewed,
                    verified_against_capture=record.extraction.verified_against_capture,
                    published_at=_midnight(record.dates.published_at.value),
                    published_at_source=(
                        record.dates.published_at.locator.selector
                        if record.dates.published_at.locator
                        else None
                    ),
                    modified_at=_midnight(record.dates.modified_at.value),
                    measured_window=record.dates.measured_window.value,
                    observed_at=record.dates.observed_at,
                )
            )
            for index, metric in enumerate(record.metrics):
                session.add(
                    ClaimMetric(
                        claim_id=record.claim_id,
                        metric_id=metric.metric_id,
                        label=metric.label,
                        comparator=metric.comparator,
                        definition=metric.definition.value or "",
                        value_text=_value_text(metric.value),
                        value_number=_as_float(metric.value.value),
                        unit=metric.unit.value or "",
                        window=metric.window.value or "",
                        scope=metric.scope.value or "",
                    )
                )
            for path, locator in record.field_locators():
                session.add(
                    ClaimLocator(
                        claim_id=record.claim_id,
                        field_path=path,
                        locator_kind=locator.kind,
                        quote=locator.quote,
                        selector=locator.selector,
                        note=locator.note,
                    )
                )
            session.flush()

        existing = session.execute(
            select(ClaimEvidence.id).where(
                ClaimEvidence.claim_id == record.claim_id,
                ClaimEvidence.capture_hash == record.evidence.capture_hash,
            )
        ).first()
        if existing is None:
            session.add(
                ClaimEvidence(
                    claim_id=record.claim_id,
                    url=record.evidence.url,
                    canonical_url=record.evidence.canonical_url,
                    capture_hash=record.evidence.capture_hash,
                    raw_sha256=record.evidence.raw_sha256,
                    snapshot_path=record.evidence.snapshot_path,
                    http_status=record.evidence.http_status,
                    robots_allowed=record.evidence.robots_allowed,
                    fetched_at=record.evidence.fetched_at,
                )
            )
        session.commit()
    return record.claim_id, created


def _midnight(value: dt.date | None) -> dt.datetime | None:
    return None if value is None else dt.datetime(value.year, value.month, value.day, tzinfo=dt.UTC)


def load_expanded_claims(
    engine: Engine,
    *,
    topic: str | None = None,
    surface: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """The expanded observation/evidence view: claim + methodology + provenance.

    Filtering, ordering and pagination run in SQL at the claim level so a request
    touches only the rows it returns (rather than expanding the whole ledger and
    slicing in Python). Ordering is newest-first by ``observed_at`` then
    ``claim_id``, a stable total order for pagination.
    """

    session_factory = sessionmaker(bind=engine, future=True)
    out: list[dict[str, Any]] = []
    with session_factory() as session:
        stmt = select(Claim)
        if topic:
            stmt = stmt.where(Claim.topic == topic)
        if surface:
            # Match every spelling of the surface (canonical id + aliases), so a
            # claim stored under an alias (e.g. "deepseek" for "deepseek-chat")
            # is found by the canonical id. Read-time only; claims are never
            # rewritten (issue #58 fixes the surface-alias read-path gap).
            from .registry import surface_id_variants

            variants = list(surface_id_variants(surface))
            if session.bind.dialect.name == "sqlite":
                clauses = [
                    func.json_extract(Claim.surfaces, "$").like(f'%"{v}"%') for v in variants
                ]
                stmt = stmt.where(or_(*clauses))
            else:
                stmt = stmt.where(
                    text("claim.surfaces::jsonb ?| CAST(:surface_variants AS text[])").bindparams(
                        surface_variants=variants
                    )
                )
        stmt = stmt.order_by(Claim.observed_at.desc(), Claim.claim_id)
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        for claim in session.execute(stmt).scalars():
            study = session.get(Study, claim.study_id)
            metrics = (
                session.execute(
                    select(ClaimMetric)
                    .where(ClaimMetric.claim_id == claim.claim_id)
                    .order_by(ClaimMetric.metric_id)
                )
                .scalars()
                .all()
            )
            locators = (
                session.execute(
                    select(ClaimLocator)
                    .where(ClaimLocator.claim_id == claim.claim_id)
                    .order_by(ClaimLocator.id)
                )
                .scalars()
                .all()
            )
            captures = (
                session.execute(
                    select(ClaimEvidence)
                    .where(ClaimEvidence.claim_id == claim.claim_id)
                    .order_by(ClaimEvidence.id)
                )
                .scalars()
                .all()
            )
            out.append(
                {
                    "claim_id": claim.claim_id,
                    "topic": claim.topic,
                    "statement": claim.statement,
                    "surfaces": claim.surfaces,
                    "status": claim.status,
                    "relationship": claim.relationship,
                    "supersedes_claim_id": claim.supersedes_claim_id,
                    "confidence": claim.confidence,
                    "confidence_detail": {
                        "score": claim.confidence_score,
                        "inputs": claim.confidence_inputs or {},
                        "rationale": claim.confidence_rationale or [],
                        "derived": True,
                    },
                    "source": {
                        "source_id": claim.source_id,
                        "publisher": study.publisher,
                        "url": study.url,
                        "canonical_url": study.canonical_url,
                        "source_class": study.source_class,
                    },
                    "dates": {
                        "published_at": _iso(claim.published_at),
                        "published_at_source": claim.published_at_source,
                        "modified_at": _iso(claim.modified_at),
                        "measured_window": claim.measured_window,
                        "observed_at": _iso(claim.observed_at),
                    },
                    "methodology": {
                        "measurement_mode": study.measurement_mode,
                        "metric_family": study.metric_family,
                        "denominator": study.denominator,
                        "prompt_universe": study.prompt_universe,
                        "sample_size": study.sample_size,
                        "unit_of_analysis": study.unit_of_analysis,
                        "time_window": study.time_window,
                        "geography": study.geography,
                        "geography_basis": study.geography_basis,
                        "language": study.language,
                        "language_basis": study.language_basis,
                        "limitations": study.limitations,
                        "methodology_notes": study.methodology_notes,
                    },
                    "metrics": [
                        {
                            "metric_id": m.metric_id,
                            "label": m.label,
                            "comparator": m.comparator,
                            "definition": m.definition,
                            "value_text": m.value_text,
                            "value_number": m.value_number,
                            "unit": m.unit,
                            "window": m.window,
                            "scope": m.scope,
                        }
                        for m in metrics
                    ],
                    "provenance": [
                        {
                            "field_path": loc.field_path,
                            "locator_kind": loc.locator_kind,
                            "quote": loc.quote,
                            "selector": loc.selector,
                            "note": loc.note,
                        }
                        for loc in locators
                    ],
                    # Raw captures are private. The product payload exposes only
                    # availability plus the content hashes — never the server
                    # filesystem path (issue #26).
                    "evidence": [
                        {
                            "capture_hash": c.capture_hash,
                            "raw_sha256": c.raw_sha256,
                            "snapshot_available": c.snapshot_path is not None,
                            "http_status": c.http_status,
                            "robots_allowed": c.robots_allowed,
                            "fetched_at": _iso(c.fetched_at),
                        }
                        for c in captures
                    ],
                    "extraction": {
                        "method": claim.extraction_method,
                        "tool": claim.extraction_tool,
                        "version": claim.extraction_version,
                        "rule_id": claim.rule_id,
                        "human_reviewed": claim.human_reviewed,
                        "verified_against_capture": claim.verified_against_capture,
                    },
                }
            )
    return out


def _iso(value: dt.datetime | None) -> str | None:
    """ISO-8601 UTC. SQLite drops tzinfo on round-trip, so a naive value is UTC."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC).isoformat()


# --------------------------------------------------------------------------- #
# Spec bundle helpers
# --------------------------------------------------------------------------- #


def load_spec_bundle(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, Mapping):
        data = data.get("claims") or []
    if not isinstance(data, list):
        raise ClaimSpecError('bundle must be a list of claim specs or {"claims": [...]}')
    return list(data)


def extraction_failures(records: Iterable[ClaimRecord], capture: Capture) -> list[str]:
    out: list[str] = []
    for record in records:
        out.extend(check_against_capture(record, capture))
    return out


__all__ = [
    "LEDGER_TABLES",
    "Capture",
    "ClaimSpecError",
    "ValidationError",
    "check_against_capture",
    "create_ledger_engine",
    "extract_capture_text",
    "extract_claim",
    "extraction_failures",
    "init_ledger",
    "load_expanded_claims",
    "load_spec_bundle",
    "persist_claim",
    "unknown",
]
