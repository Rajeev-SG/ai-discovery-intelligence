"""Regression: the automated extraction lane must persist quote-verified claims.

``extract_pending_claims`` is the unattended production lane (Dagster asset →
Oracle timer). It must mark each quote-verified claim reviewed, because every
locator it accepts was deterministically checked against the capture. If it
leaves ``human_reviewed=False``, the ledger's provenance validator rejects every
``llm_proposal`` claim and the lane silently persists nothing — the exact
production failure this test pins against (issue #9).
"""

from __future__ import annotations

import datetime as dt

import pytest
import sqlalchemy as sa

from ai_discovery import claims as C
from ai_discovery.claim_pipeline import extract_pending_claims
from ai_discovery.models import EvidenceItem, Source
from ai_discovery.semantic import (
    ExtractedClaim,
    ExtractedMetric,
    SemanticExtractionResult,
)

QUOTE = "ChatGPT's web traffic share fell from 76.4% one year ago to around 52.7% one month ago."
CAPTURE_TEXT = "Similarweb research. " + QUOTE + " The panel covers opt-in devices worldwide."


def _result() -> SemanticExtractionResult:
    metric = ExtractedMetric(
        label="ChatGPT share of AI-chatbot web traffic",
        value=52.7,
        value_quote="around 52.7% one month ago",
        unit="%",
        unit_quote="around 52.7%",
        definition="share of all AI-chatbot web traffic",
        definition_quote=QUOTE,
        window="one month ago",
        window_quote="around 52.7% one month ago",
        scope="all AI chatbot web traffic",
        scope_quote="around 52.7% one month ago",
    )
    claim = ExtractedClaim(
        topic="audience_usage",
        statement=(
            "Similarweb estimates ChatGPT at ~52.7% of all AI-chatbot web traffic, "
            "down from 76.4% a year earlier."
        ),
        surfaces=["chatgpt"],
        measurement_mode="vendor_estimate",
        metric_family="share of measured AI-chatbot web traffic",
        metric_family_quote=QUOTE,
        denominator="all AI chatbot web traffic (visits), worldwide",
        denominator_quote=QUOTE,
        unit_of_analysis="domain-level monthly visits",
        unit_of_analysis_quote=QUOTE,
        time_window="one month before publication",
        time_window_quote="around 52.7% one month ago",
        methodology_notes="panel + ISP + public data + ML models",
        methodology_notes_quote=QUOTE,
        capture_anchor=QUOTE,
        metrics=[metric],
    )
    return SemanticExtractionResult(claims=[claim], model="fake-model", attempts=1)


class _FakeClient:
    """Stand-in for the Instructor/OpenRouter client; returns a fixture-shaped result."""

    def __init__(self, result: SemanticExtractionResult) -> None:
        self._result = result

    def run(self, **_kwargs: object) -> SemanticExtractionResult:
        return self._result


@pytest.fixture
def ledger_db(tmp_path, monkeypatch):
    """A sqlite evidence DB + snapshot dir wired into settings for the lane."""
    db_url = f"sqlite+pysqlite:///{tmp_path / 'evidence.db'}"
    monkeypatch.setenv("AI_DISCOVERY_DATABASE_URL", db_url)
    monkeypatch.setenv("AI_DISCOVERY_SNAPSHOT_DIR", str(tmp_path / "snapshots"))
    from ai_discovery import db as dbmod
    from ai_discovery import settings as settingsmod

    settingsmod.get_settings.cache_clear()
    dbmod._engine = None
    dbmod._SessionLocal = None

    engine = sa.create_engine(db_url, future=True)
    from ai_discovery.models import Base

    Base.metadata.create_all(engine)
    C.init_ledger(engine)
    yield engine
    engine.dispose()


def _seed_evidence(engine, capture_hash: str) -> None:
    from sqlalchemy.orm import Session

    from ai_discovery.snapshot_store import store_extracted_text

    store_extracted_text(capture_hash, CAPTURE_TEXT)
    url = "https://www.similarweb.com/blog/research/market-research/most-visited-websites/"
    with Session(engine) as session:
        session.add(
            Source(
                id="similarweb-most-visited-websites",
                publisher="Similarweb",
                source_class="vendor_research",
                url=url,
                topics=[],
                preferred_fetch="http",
                fetch_mode="http",
                enabled=True,
            )
        )
        session.add(
            EvidenceItem(
                id="ev1",
                source_id="similarweb-most-visited-websites",
                url=url,
                canonical_url=url,
                title="Similarweb research",
                publisher="Similarweb",
                source_class="vendor_research",
                observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
                capture_hash=capture_hash,
                fetch_mode="http",
                topics=[],
            )
        )
        session.commit()


def test_automated_lane_persists_a_quote_verified_claim(ledger_db, monkeypatch):
    from ai_discovery import claim_pipeline

    capture_hash = "a" * 64
    _seed_evidence(ledger_db, capture_hash)

    # Feed the fake result through the same semantic_extract seam the lane uses.
    monkeypatch.setattr(claim_pipeline, "semantic_extract", lambda **_kw: _result())
    from ai_discovery.db import session_scope

    with session_scope() as session:
        run = extract_pending_claims(session, limit=5)

    assert run.captures_seen == 1
    assert run.captures_failed == 0, run.failures
    assert run.claims_created == 1, (
        "the automated lane must persist the quote-verified claim; 0 means the "
        "provenance guard rejected an unreviewed llm_proposal"
    )
    rows = C.load_expanded_claims(ledger_db)
    assert len(rows) == 1

    # Claims -> change_events: the validated claim yields one typed, dated event
    # linked back to the claim, so the observation plane's event feed is real.
    from sqlalchemy.orm import Session

    from ai_discovery.observations import load_events

    with Session(ledger_db) as s2:
        events = load_events(s2)
    assert len(events) == 1, "a validated claim must produce one change event"
    event = events[0]
    assert event.event_type.value == "audience_shift"
    assert event.claims == [rows[0]["claim_id"]]
    assert event.surfaces == ["chatgpt"]
    assert run.events_created == 1


def test_no_change_topic_yields_no_event(ledger_db, monkeypatch):
    """An implication is not a change: it must not fabricate an event."""
    from ai_discovery import claim_pipeline

    capture_hash = "b" * 64
    _seed_evidence(ledger_db, capture_hash)

    result = _result()
    # optimisation_implication is an implication, not a market change.
    result.claims[0].topic = "optimisation_implication"
    monkeypatch.setattr(claim_pipeline, "semantic_extract", lambda **_kw: result)
    from ai_discovery.db import session_scope

    with session_scope() as session:
        run = extract_pending_claims(session, limit=5)

    assert run.claims_created == 1, run.failures
    assert run.events_created == 0, "an implication must not produce a change event"

    from sqlalchemy.orm import Session

    from ai_discovery.observations import load_events

    with Session(ledger_db) as s2:
        assert load_events(s2) == []
