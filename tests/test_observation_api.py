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
