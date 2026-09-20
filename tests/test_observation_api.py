"""Issue #23: claims/events/brief read paths and the surface evidence projection."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_claims import _spec, _synthetic_capture

from ai_discovery import api
from ai_discovery import claims as C
from ai_discovery.change_events import ChangeEvent, EventType
from ai_discovery.models import Base
from ai_discovery.observations import persist_brief, persist_events


def _claim_record(**overrides):
    capture = _synthetic_capture()
    return C.extract_claim(spec=_spec(**overrides), capture=capture)


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'obs.db'}")
    Base.metadata.create_all(engine)
    C.init_ledger(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()

    # A real, validated claim linked to a surface.
    session.add_all([])  # no-op keeps the fixture shape explicit
    C.persist_claim(engine, _claim_record())

    api.app.dependency_overrides[api.get_db] = lambda: session
    with TestClient(api.app) as test_client:
        yield test_client, session, engine
    api.app.dependency_overrides.clear()
    session.close()


def test_claims_endpoint_returns_validated_claim_without_private_paths(client):
    c, _session, _engine = client
    body = c.get("/claims").json()
    assert body["total"] == 1
    claim = body["items"][0]
    assert claim["statement"]
    assert claim["value"][0]["known"] is True
    assert claim["confidence"] in ("high", "medium", "low", "unknown")
    assert claim["confidence_detail"]["derived"] is True
    assert claim["confidence_detail"]["inputs"]
    assert claim["freshness"]["state"] in ("fresh", "recent", "aging", "stale", "unknown")
    # Privacy boundary: hash + availability, never the private path.
    for entry in claim["evidence"]:
        assert "snapshot_path" not in entry
        assert "snapshot_available" in entry
    assert "snapshot_path" not in c.get("/claims").text


def test_claims_endpoint_filters_by_surface(client):
    c, _session, _engine = client
    assert c.get("/claims?surface=widget-search").json()["total"] == 1
    assert c.get("/claims?surface=never-a-surface").json()["total"] == 0


def test_events_endpoint_reads_persisted_events(client):
    c, session, _engine = client
    assert c.get("/events").json()["count"] == 0
    persist_events(
        session,
        [
            ChangeEvent(
                event_type=EventType.product_launch,
                title="Widget Search launched",
                description="A new surface.",
                surfaces=["widget-search"],
                claims=["c1"],
                observed_at=dt.datetime(2026, 9, 10, tzinfo=dt.UTC),
                published_at=dt.datetime(2026, 9, 9, tzinfo=dt.UTC),
            )
        ],
    )
    body = c.get("/events").json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Widget Search launched"
    assert body["items"][0]["event_type"] == "product_launch"
    assert c.get("/events?surface=widget-search").json()["count"] == 1
    assert c.get("/events?surface=nope").json()["count"] == 0


def test_brief_endpoint_is_explicit_when_empty_then_reads_real_output(client):
    c, session, _engine = client
    empty = c.get("/brief").json()
    assert empty["state"] == "empty"
    assert empty["items"] == []

    persist_brief(
        session,
        {
            "total_candidates": 2,
            "items": [{"change": "real brief item", "confidence": "medium", "significance": 4.0}],
        },
    )
    body = c.get("/brief").json()
    assert body["state"] == "ready"
    assert body["items"][0]["change"] == "real brief item"


def test_surface_evidence_shows_real_evidence_and_explicit_no_evidence(client):
    c, _session, _engine = client
    evidenced = c.get("/surfaces/widget-search/evidence").json()
    assert evidenced["evidence_state"] == "evidenced"
    assert evidenced["claims"]

    none_state = c.get("/surfaces/no-such-surface/evidence").json()
    assert none_state["evidence_state"] == "no_evidence"
    assert none_state["claims"] == []
    assert none_state["evidence_note"]


def test_reconciliation_endpoint_is_removed(client):
    """The hardcoded reconciliation output must not remain as a fake read path."""

    c, _session, _engine = client
    assert c.get("/reconciliation/canonical").status_code == 404


def test_claims_and_events_are_newest_first_with_multiple_items(client):
    """Issue #23 F2: ordering must hold, and the event limit applies after sorting."""

    c, session, engine = client
    # A second claim, older than the first.
    older = _claim_record(
        statement="Widget Search had 0.9M monthly visits in December 2025.",
        topic="audience_usage",
    )
    C.persist_claim(engine, older)

    # SQL-side pagination: limit/offset page the ledger without overlap.
    all_ids = [i["claim_id"] for i in c.get("/claims").json()["items"]]
    assert len(all_ids) >= 2
    first_page = [i["claim_id"] for i in c.get("/claims?limit=1").json()["items"]]
    second_page = [i["claim_id"] for i in c.get("/claims?limit=1&offset=1").json()["items"]]
    assert first_page == all_ids[:1]
    assert second_page == all_ids[1:2]
    assert not set(first_page) & set(second_page)
    # A surface filter is applied in SQL too.
    assert c.get("/claims?surface=never").json()["total"] == 0

    persist_events(
        session,
        [
            ChangeEvent(
                event_type=EventType.product_launch,
                title="newer",
                description=".",
                surfaces=["widget-search"],
                observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
                published_at=dt.datetime(2026, 9, 15, tzinfo=dt.UTC),
            ),
            ChangeEvent(
                event_type=EventType.product_launch,
                title="older",
                description=".",
                surfaces=["widget-search"],
                observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
                published_at=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            ),
        ],
    )
    titles = [e["title"] for e in c.get("/events").json()["items"]]
    assert titles[0] == "newer", titles
    # limit still returns the newest, never a stale page.
    assert c.get("/events?limit=1").json()["items"][0]["title"] == "newer"


def test_provenance_quotes_are_bounded_and_allow_listed(client):
    """Issue #23 F3: provenance is an allow-list with a bounded excerpt, not raw text."""

    c, _session, _engine = client
    claim = c.get("/claims").json()["items"][0]
    for p in claim["provenance"]:
        assert set(p) == {"field_path", "locator_kind", "quote", "selector"}
        if p["quote"]:
            assert len(p["quote"]) <= 301


def test_degraded_ledger_without_event_tables_is_operator_visible(client, caplog):
    """Issue #23 F4: a pre-migration ledger logs a warning instead of failing silently."""

    c, session, _engine = client
    # Drop the event table to simulate a ledger predating migration 0004.
    from sqlalchemy import text as _text

    session.execute(_text("DROP TABLE IF EXISTS change_event"))
    session.commit()
    with caplog.at_level("WARNING"):
        body = c.get("/events").json()
    assert body["count"] == 0
    assert any("change_event" in r.message for r in caplog.records)


def test_surface_evidence_resolves_aliases_like_the_mechanics_path(client):
    """Issue #58: a surface whose claims are stored under an alias must resolve to
    the canonical registry id in the evidence read path too, so it renders its
    evidence instead of a false "No evidence" (the gap #58 fixes)."""

    c, _session, engine = client
    # A real, validated claim stored under the alias "deepseek" (not the registry
    # id "deepseek-chat"). Distinct content so it is not deduped against the
    # fixture's widget-search claim.
    C.persist_claim(
        engine,
        _claim_record(
            surfaces=["deepseek"],
            statement="DeepSeek had 9.9M monthly visits in February 2026.",
        ),
    )

    aliased = c.get("/surfaces/deepseek-chat/evidence").json()
    assert aliased["evidence_state"] == "evidenced"
    assert aliased["claims"]

    # The same claim is found by the per-surface claims filter.
    assert c.get("/claims?surface=deepseek-chat").json()["total"] == 1

    # The bulk projection is keyed by the canonical id, not the raw alias.
    bulk = c.get("/surface-evidence").json()["surfaces"]
    assert "deepseek-chat" in bulk
    assert "deepseek" not in bulk


def test_mechanics_endpoint_inlines_reconciliation_for_conflicting_claims(client, monkeypatch):
    """Issue #58: the mechanics endpoint joins the backend reconciliation index onto
    each evidence entry, so a conflict renders inline without React re-deriving it."""

    c, _session, _engine = client
    # Two real-shaped ledger rows that disagree on the same surface/subject/metric.
    # Monkeypatch the ledger read so the test exercises the API wiring, not
    # extraction (the alias path already has its own end-to-end test).
    def _row(visits, claim_id):
        return {
            "claim_id": claim_id,
            "topic": "retrieval_index",
            "statement": f"ChatGPT retrieved ~{visits} results per query.",
            "surfaces": ["chatgpt"],
            "status": "current",
            "relationship": "new",
            "confidence": "medium",
            "confidence_detail": {"score": 0.5, "inputs": {}, "rationale": [], "derived": True},
            "source": {
                "source_id": "s",
                "publisher": "P",
                "url": "https://example.test/x",
                "source_class": "official",
            },
            "dates": {"published_at": "2026-01-02", "observed_at": "2026-09-16T00:00:00+00:00"},
            "methodology": {"measurement_mode": "vendor_estimate"},
            "metrics": [
                {
                    "metric_id": "count",
                    "label": "Results per query",
                    "value_number": visits,
                    "unit": "results",
                }
            ],
            "provenance": [],
            "evidence": [],
            "extraction": {},
        }

    rows = [_row(2.4, "cr1"), _row(0.6, "cr2")]
    monkeypatch.setattr("ai_discovery.claims.load_expanded_claims", lambda *a, **k: rows)

    body = c.get("/mechanics").json()
    surface = body["surfaces"].get("chatgpt")
    assert surface is not None
    recon_seen = [
        rec
        for dim in surface["dimensions"]
        for a in dim["assertions"]
        for e in a["evidence"]
        for rec in e["reconciliation"]
    ]
    assert recon_seen, "expected an inline reconciliation record for differing claims"
    assert all(rec["state"] and rec["relationship"] for rec in recon_seen)
