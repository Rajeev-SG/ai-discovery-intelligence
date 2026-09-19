"""Extraction-lane orchestration: new capture → Instructor claims → ledger.

One asset owns the automated cycle: for every changed (or never-extracted)
cleaned snapshot in the evidence feed, run Instructor + OpenRouter extraction,
verify every quote against the capture, persist validated claims, and surface
the run summary for the API/brief layer. No human is in the loop.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .change_derivation import derive_and_persist
from .claim_extract import claims_from_extraction
from .claims import Capture, create_ledger_engine, persist_claim
from .models import EvidenceItem
from .semantic import DEFAULT_MODEL, semantic_extract
from .settings import get_settings


@dataclass
class ExtractionRun:
    """Run summary: what was extracted, what failed, and model telemetry."""

    captures_seen: int = 0
    captures_extracted: int = 0
    captures_failed: int = 0
    claims_created: int = 0
    claims_skipped: int = 0
    events_created: int = 0
    failures: list[dict] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cost_known_calls: int = 0

    def as_dict(self) -> dict:
        return {
            "captures_seen": self.captures_seen,
            "captures_extracted": self.captures_extracted,
            "captures_failed": self.captures_failed,
            "claims_created": self.claims_created,
            "events_created": self.events_created,
            "failures": self.failures,
            "semantic_tokens_in": self.tokens_in,
            "semantic_tokens_out": self.tokens_out,
            "semantic_cost_usd": round(self.cost_usd, 6),
            "semantic_cost_known_calls": self.cost_known_calls,
        }


def extract_pending_claims(
    session: Session,
    *,
    limit: int | None = 20,
    client=None,
    model: str = DEFAULT_MODEL,
) -> ExtractionRun:
    """Extract claims for evidence items that have no claim yet.

    A capture is skipped when its capture_hash already appears in the ledger
    (same assertion re-extracted from the same source is the same claim), so
    model spend is bounded by change detection.
    """
    from .claims import Claim, ClaimEvidence

    run = ExtractionRun()

    evidence = list(
        session.scalars(
            select(EvidenceItem).order_by(EvidenceItem.observed_at.desc()).limit(limit or 20)
        ).all()
    )
    for item in evidence:
        run.captures_seen += 1
        existing = (
            session.query(Claim)
            .join(ClaimEvidence, Claim.claim_id == ClaimEvidence.claim_id)
            .filter(ClaimEvidence.capture_hash == item.capture_hash)
            .first()
        )
        if existing is not None:
            continue
        text = None
        from .snapshot_store import read_extracted_text

        stored = read_extracted_text(item.capture_hash)
        text = stored
        if not text:
            run.failures.append(
                {"capture_hash": item.capture_hash, "error": "no extracted text stored"}
            )
            continue
        capture = Capture(
            raw=b"",
            text=text,
            fetched_at=item.observed_at or dt.datetime.now(dt.UTC),
        )
        # The raw hash is what the model audit trail records; when the evidence
        # row has one, use it. A pure-text rebuild still verifies every quote.
        capture.raw = (item.raw_sha256 or "").encode() or b""
        source = {
            "source_id": item.source_id or "discovered-candidate",
            "publisher": item.publisher or "",
            "url": item.url,
            "canonical_url": item.canonical_url,
            "source_class": item.source_class,
            "snapshot_path": item.snapshot_path,
            "http_status": item.http_status,
            "robots_allowed": None,
        }
        try:
            result = semantic_extract(
                source_id=item.source_id or "discovered-candidate",
                source_url=item.canonical_url or item.url,
                cleaned_markdown=text,
                client=client,
                model=model,
            )
            # Every declared locator is deterministically checked against the
            # capture bytes inside claims_from_extraction
            # (check_against_capture). That is the honest property this
            # unattended lane establishes, so it asserts
            # verified_against_capture=True — never human_reviewed, which would
            # falsely claim a person read the model output.
            claims = claims_from_extraction(
                result,
                source=source,
                capture=capture,
                verified_against_capture=True,
            )
        except Exception as error:  # noqa: BLE001 — surfaced per capture, never fatal
            run.captures_failed += 1
            run.failures.append({"capture_hash": item.capture_hash[:12], "error": str(error)[:300]})
            continue
        run.captures_extracted += 1
        run.tokens_in += result.tokens_in or 0
        run.tokens_out += result.tokens_out or 0
        if result.cost_known and result.cost_usd is not None:
            run.cost_known_calls += 1
            run.cost_usd += result.cost_usd
        ledger_engine = create_ledger_engine(get_settings().database_url)
        for claim in claims:
            _, created = persist_claim(ledger_engine, record=claim)
            if created:
                run.claims_created += 1
        ledger_engine.dispose()
        # Claims → change_events: derive a typed, dated event per validated claim
        # on the same ledger session (idempotent by claim id), so the observation
        # plane and the brief see real changes, not an empty event feed.
        run.events_created += derive_and_persist(session, claims)
    return run
