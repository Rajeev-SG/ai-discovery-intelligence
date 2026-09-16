"""Dedup test: re-observation of identical text does not duplicate evidence."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from ai_discovery.models import Base, EvidenceItem
from ai_discovery.store import store_articles as store_evidence


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _item(**kw):
    base = {
        "canonical_url": "https://example.com/page",
        "url": "https://example.com/page",
        "title": "T",
        "publisher": "P",
        "source_class": "official",
        "topics": ["t"],
        "capture_hash": "abc123",
        "text_chars": 100,
        "excerpt": "excerpt",
        "fetch_mode": "http",
    }
    return {**base, **kw}


def test_identical_capture_not_duplicated(session):
    store_evidence(session, [_item()])
    store_evidence(session, [_item()])  # same canonical_url + capture_hash
    rows = session.scalars(select(EvidenceItem)).all()
    assert len(rows) == 1


def test_different_capture_creates_new_row(session):
    store_evidence(session, [_item()])
    store_evidence(session, [_item(capture_hash="def456")])
    rows = session.scalars(select(EvidenceItem)).all()
    assert len(rows) == 2
