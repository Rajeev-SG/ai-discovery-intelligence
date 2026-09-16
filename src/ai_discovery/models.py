"""Canonical persistence models (SQLAlchemy 2.0).

PostgreSQL is canonical. Raw snapshots stay private on disk and are referenced
here only by hash/path. History is append-only: evidence rows are never
overwritten in place; a new capture creates a new row.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    pass


class Source(Base):
    """A configured source asset (mirror of config/sources.yaml) plus its health."""

    __tablename__ = "source"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    publisher: Mapped[str] = mapped_column(String(200))
    source_class: Mapped[str] = mapped_column(String(60), index=True)
    url: Mapped[str] = mapped_column(Text)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    preferred_fetch: Mapped[str] = mapped_column(String(40))
    fetch_mode: Mapped[str] = mapped_column(
        String(40)
    )  # resolved: rss|api|http|sitemap|rsshub|browser
    fetch_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # health / freshness
    health_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    last_check_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_content_hash: Mapped[str | None] = mapped_column(String(64))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    checks: Mapped[list[SourceCheck]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceCheck(Base):
    """One health observation for a source (history, not overwritten)."""

    __tablename__ = "source_check"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source.id", ondelete="CASCADE"), index=True)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(30))  # ok|empty|error|blocked|robots_denied
    http_status: Mapped[int | None] = mapped_column(Integer)
    http_headers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    content_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="checks")


class DiscoveredCandidate(Base):
    """A URL found by the discovery lane. Non-canonical until validated."""

    __tablename__ = "discovered_candidate"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # sha256(canonical_url)[:32]
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, index=True)
    host: Mapped[str] = mapped_column(String(200), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    discovered_via: Mapped[str] = mapped_column(String(40))  # gdelt|google_news|searxng|rsshub
    discovery_query: Mapped[str | None] = mapped_column(Text)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_class_guess: Mapped[str | None] = mapped_column(String(60))
    in_registry: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="unvalidated", index=True)
    validation_notes: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[list[EvidenceItem]] = relationship(back_populates="candidate")


class EvidenceItem(Base):
    """A captured, normalised piece of public evidence."""

    __tablename__ = "evidence_item"
    __table_args__ = (Index("ix_evidence_canonical_capture", "canonical_url", "capture_hash"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("source.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovered_candidate.id", ondelete="SET NULL"), nullable=True, index=True
    )

    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, index=True)
    title: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(200), index=True)
    source_class: Mapped[str] = mapped_column(String(60), index=True)

    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    published_at_source: Mapped[str | None] = mapped_column(
        String(30)
    )  # feed|json_ld|meta|url|none
    modified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    topics: Mapped[list[str]] = mapped_column(JSON, default=list)
    language: Mapped[str | None] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(20))

    capture_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256 of extracted text
    raw_sha256: Mapped[str | None] = mapped_column(String(64))  # sha256 of raw bytes
    text_chars: Mapped[int | None] = mapped_column(Integer)
    excerpt: Mapped[str | None] = mapped_column(Text)

    fetch_mode: Mapped[str] = mapped_column(String(40))
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(120))
    etag: Mapped[str | None] = mapped_column(String(200))
    http_last_modified: Mapped[str | None] = mapped_column(String(120))
    extractor: Mapped[str | None] = mapped_column(String(60))
    snapshot_path: Mapped[str | None] = mapped_column(Text)  # private, hash-addressed
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="validated")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped[Source | None] = relationship()
    candidate: Mapped[DiscoveredCandidate | None] = relationship(back_populates="evidence")
