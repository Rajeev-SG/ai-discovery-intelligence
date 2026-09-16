"""API contract tests against a temporary SQLite database."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_discovery import api
from ai_discovery.hashing import canonicalise_url, evidence_id, sha256_text
from ai_discovery.models import Base, DiscoveredCandidate, EvidenceItem, Source


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(
        Source(
            id="ahrefs-most-cited-domains",
            publisher="Ahrefs",
            source_class="visibility_research",
            url="https://ahrefs.com/blog/most-cited-domains-in-chatgpt/",
            topics=["citations"],
            preferred_fetch="http",
            fetch_mode="http",
            health_status="ok",
            last_success_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
        )
    )
    url = "https://ahrefs.com/blog/most-cited-domains-in-chatgpt/"
    text = "Reddit is the largest cited domain at 16.8% share."
    session.add(
        EvidenceItem(
            id=evidence_id(canonicalise_url(url), sha256_text(text)),
            source_id="ahrefs-most-cited-domains",
            url=url,
            canonical_url=canonicalise_url(url),
            title="The 50 Most-Cited Websites in ChatGPT",
            publisher="Ahrefs",
            source_class="visibility_research",
            published_at=dt.datetime(2025, 9, 10, tzinfo=dt.UTC),
            modified_at=dt.datetime(2026, 9, 2, tzinfo=dt.UTC),
            observed_at=dt.datetime(2026, 9, 16, tzinfo=dt.UTC),
            topics=["citations"],
            capture_hash=sha256_text(text),
            text_chars=len(text),
            excerpt=text,
            fetch_mode="http",
            http_status=200,
            extractor="trafilatura",
            snapshot_path="/private/snap",
        )
    )
    session.add(
        DiscoveredCandidate(
            id="abc123",
            url="https://news.example.com/aeo-study",
            canonical_url="https://news.example.com/aeo-study",
            host="news.example.com",
            title="An AEO study",
            discovered_via="bing_news",
            topics=["aeo"],
            source_class_guess="visibility_research",
            in_registry=False,
            validation_status="unvalidated",
        )
    )
    session.commit()

    api.app.dependency_overrides[api.get_db] = lambda: session
    with TestClient(api.app) as test_client:
        yield test_client
    api.app.dependency_overrides.clear()
    session.close()


def test_evidence_feed_returns_required_shape(client):
    body = client.get("/evidence?limit=100").json()
    assert body["total"] == 1
    item = body["items"][0]
    for field in [
        "id", "url", "title", "publisher", "source_class", "published_at",
        "modified_at", "observed_at", "topics", "capture_hash", "excerpt",
        "validation_status", "is_candidate",
    ]:
        assert field in item, field
    assert item["published_at"].startswith("2025-09-10")
    assert item["modified_at"].startswith("2026-09-02")
    assert item["published_at"] != item["modified_at"]


def test_evidence_never_exposes_private_snapshot_path(client):
    body = client.get("/evidence?limit=100").json()
    assert "snapshot_path" not in body["items"][0]
    assert body["items"][0]["snapshot_available"] is True


def test_evidence_filters(client):
    assert client.get("/evidence?source_class=visibility_research").json()["count"] == 1
    assert client.get("/evidence?source_class=official").json()["count"] == 0
    assert client.get("/evidence?topic=citations").json()["count"] == 1
    assert client.get("/evidence?q=Most-Cited").json()["count"] == 1


def test_sources_endpoint_exposes_health(client):
    body = client.get("/sources").json()
    assert body["count"] == 1
    assert body["items"][0]["health_status"] == "ok"
    assert body["items"][0]["last_success_at"]


def test_candidates_default_hides_registry_entries(client):
    body = client.get("/candidates").json()
    assert body["count"] == 1
    assert body["items"][0]["in_registry"] is False
    assert body["items"][0]["validation_status"] == "unvalidated"


def test_health_counts(client):
    body = client.get("/health").json()
    assert body["evidence_items"] == 1
    assert body["sources"] == 1
