"""Regression: the automated extraction lane must persist quote-verified claims.

``extract_pending_claims`` is the unattended production lane (Dagster asset →
Oracle timer). It must mark each quote-verified claim reviewed, because every
locator it accepts was deterministically checked against the capture. If it
leaves both review flags false, the ledger's provenance validator rejects every
``llm_proposal`` claim and the lane silently persists nothing — the exact
production failure this test pins against (issue #9). It asserts
``verified_against_capture``, the honest property an unattended lane establishes,
and never ``human_reviewed``.
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
        "provenance guard rejected an llm_proposal with no review flag"
    )
    rows = C.load_expanded_claims(ledger_db)
    assert len(rows) == 1
    # Honest provenance: the lane may assert deterministic capture verification,
    # never human_reviewed (no person read the model output).
    prov = rows[0]["extraction"]
    assert prov["verified_against_capture"] is True
    assert prov["human_reviewed"] is False

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


def test_event_id_is_content_addressed_not_prefix_sliced():
    """A corrected claim (same id, new content) must yield a DISTINCT event id."""
    from ai_discovery.change_derivation import event_from_claim

    base = _result().claims[0]

    def _record(claim):
        from ai_discovery.claim_extract import claim_from_extracted
        from ai_discovery.claims import Capture

        text = CAPTURE_TEXT
        cap = Capture(raw=b"", text=text, fetched_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC))
        src = {
            "source_id": "similarweb-most-visited-websites",
            "publisher": "Similarweb",
            "url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
            "canonical_url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
            "source_class": "vendor_research",
            "http_status": 200,
        }
        return claim_from_extracted(claim, source=src, capture=cap, verified_against_capture=True)

    rec_a = _record(base)
    # Same claim id (topic/statement/source) but a changed statement would change
    # the claim id, so instead vary a metric value that does not feed claim_id.
    corrected = base.model_copy(deep=True)
    corrected.metrics[0].value = 52.9
    corrected.metrics[0].value_quote = "around 52.7% one month ago"  # quote still valid
    rec_b = _record(corrected)

    assert rec_a.claim_id == rec_b.claim_id, "claim id must be stable for this test"
    ev_a = event_from_claim(rec_a)
    ev_b = event_from_claim(rec_b)
    assert ev_a.id != ev_b.id, "a corrected claim must produce a distinct event id"
    # Idempotent: the same content derives the same id every time.
    assert event_from_claim(rec_a).id == ev_a.id


def test_persist_events_is_idempotent_and_appends_distinct(ledger_db):
    from sqlalchemy.orm import Session

    from ai_discovery.change_derivation import event_from_claim
    from ai_discovery.claim_extract import claim_from_extracted
    from ai_discovery.claims import Capture
    from ai_discovery.observations import load_events, persist_events

    cap = Capture(raw=b"", text=CAPTURE_TEXT, fetched_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC))
    src = {
        "source_id": "similarweb-most-visited-websites",
        "publisher": "Similarweb",
        "url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "canonical_url": "https://www.similarweb.com/blog/research/market-research/most-visited-websites/",
        "source_class": "vendor_research",
        "http_status": 200,
    }
    rec = claim_from_extracted(
        _result().claims[0], source=src, capture=cap, verified_against_capture=True
    )
    ev = event_from_claim(rec)

    with Session(ledger_db) as s:
        assert persist_events(s, [ev]) == 1
        assert persist_events(s, [ev]) == 0, "same event id must be a no-op"
        assert len(load_events(s)) == 1


def test_provenance_validator_accepts_all_three_honest_combinations():
    """The three admissible flag combinations, and the one that must be rejected."""
    from pydantic import ValidationError

    from ai_discovery.claim_models import ExtractionProvenance

    # deterministic parser: no review flag needed.
    ok = ExtractionProvenance(method="deterministic_parser", tool="t", version="v")
    assert ok.human_reviewed is False and ok.verified_against_capture is False

    # human reviewed, unattended-verified, and both: all admissible.
    for kwargs in (
        {"human_reviewed": True, "verified_against_capture": False},
        {"human_reviewed": False, "verified_against_capture": True},
        {"human_reviewed": True, "verified_against_capture": True},
    ):
        prov = ExtractionProvenance(method="llm_proposal", tool="t", version="v", **kwargs)
        assert prov.human_reviewed == kwargs["human_reviewed"]
        assert prov.verified_against_capture == kwargs["verified_against_capture"]

    # Neither flag: an unreviewed, unverified llm_proposal is never evidence.
    with pytest.raises(ValidationError):
        ExtractionProvenance(method="llm_proposal", tool="t", version="v")
