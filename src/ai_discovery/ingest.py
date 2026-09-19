"""Lane orchestration: registry acquisition + discovery.

Transport is the direct crawler (crawler.py: robots gate + HTTP + Crawl4AI
render fallback); this module sequences the lanes, persists results and
returns a run summary. Dagster owns scheduling and run history.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .crawler import build_query_jobs, build_source_jobs, run_discovery_jobs, run_registry_lane_jobs
from .discovery import candidate_urls
from .models import Source
from .registry import SourcesConfig, resolve_fetch_mode
from .store import store_articles, store_candidates, store_statuses


@dataclass
class LaneResult:
    lane: str
    sources_attempted: int = 0
    items_new: int = 0
    candidates_new: int = 0
    statuses: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "lane": self.lane,
            "sources_attempted": self.sources_attempted,
            "items_new": self.items_new,
            "candidates_new": self.candidates_new,
            "statuses": self.statuses,
            "failures": self.failures,
        }


def upsert_sources(session: Session, config: SourcesConfig) -> list[Source]:
    """Mirror config/sources.yaml into the source table (config is the source of truth)."""
    existing = {s.id: s for s in session.scalars(select(Source)).all()}
    for cfg in config.sources:
        mode, fetch_url = resolve_fetch_mode(cfg)
        source = existing.get(cfg.id)
        if source is None:
            source = Source(id=cfg.id)
            session.add(source)
        source.publisher = cfg.publisher
        source.source_class = cfg.source_class
        source.url = cfg.url
        source.topics = cfg.topics
        source.preferred_fetch = cfg.preferred_fetch
        source.fetch_mode = mode
        source.fetch_url = fetch_url
        source.region = cfg.region
        source.language = cfg.language
        source.enabled = cfg.enabled
    session.flush()
    return list(session.scalars(select(Source)).all())


def run_registry_lane(
    session: Session,
    config: SourcesConfig,
    *,
    source_ids: list[str] | None = None,
    limit: int | None = None,
) -> LaneResult:
    upsert_sources(session, config)
    session.flush()
    jobs = build_source_jobs(config, source_ids=source_ids, limit=limit)
    result = LaneResult(lane="registry", sources_attempted=len(jobs))
    if not jobs:
        return result
    sinks = run_registry_lane_jobs(jobs)
    session.flush()
    result.items_new = store_articles(session, sinks.items)
    store_statuses(session, sinks.statuses)
    result.statuses = sinks.statuses
    return result


def run_discovery_lane(
    session: Session,
    config: SourcesConfig,
    *,
    providers: list[str] | None = None,
    max_per_query: int = 10,
) -> LaneResult:
    jobs = build_query_jobs(config, providers=providers)
    result = LaneResult(lane="discovery", sources_attempted=len(jobs))
    if not jobs:
        return result
    sinks = run_discovery_jobs([{**q, "max_results": max_per_query} for q in jobs])
    result.candidates_new = store_candidates(session, sinks.candidates, config.registered_hosts())
    result.failures = sinks.failures
    return result


def ingest_all(
    session: Session,
    config: SourcesConfig,
    *,
    source_ids: list[str] | None = None,
    limit: int | None = None,
    max_per_query: int = 10,
) -> dict:
    """Run both lanes sequentially and persist their outputs."""
    upsert_sources(session, config)
    session.flush()
    source_jobs = build_source_jobs(config, source_ids=source_ids, limit=limit)
    query_jobs = [{**q, "max_results": max_per_query} for q in build_query_jobs(config)]
    acq_sinks = run_registry_lane_jobs(source_jobs)
    disc_sinks = run_discovery_jobs(query_jobs)
    session.flush()
    registry = LaneResult(lane="registry", sources_attempted=len(source_jobs))
    registry.items_new = store_articles(session, acq_sinks.items)
    store_statuses(session, acq_sinks.statuses)
    registry.statuses = acq_sinks.statuses
    discovery = LaneResult(lane="discovery", sources_attempted=len(query_jobs))
    discovery.candidates_new = store_candidates(
        session, disc_sinks.candidates, config.registered_hosts()
    )
    discovery.failures = disc_sinks.failures
    session.flush()
    return {"registry": registry.as_dict(), "discovery": discovery.as_dict()}


CONSENT_SHELL_TITLES = {
    "guce",
    "consent",
    "before you continue",
    "access denied",
    "just a moment",
    "latest world & national news & headlines",
    "news",
    "home",
}
CONSENT_SHELL_MARKERS = (
    "guce",
    "consent.yahoo.com",
    "consent.google.com",
    "privacy-consent",
    "cf-challenge",
)


def _is_low_quality(item: dict, *, min_chars: int) -> str | None:
    """Return a rejection reason, or None when the capture looks like real content."""
    title = (item.get("title") or "").strip().lower()
    canonical = (item.get("canonical_url") or "").lower()
    if title in CONSENT_SHELL_TITLES:
        return "consent/redirect shell title"
    if any(marker in canonical for marker in CONSENT_SHELL_MARKERS):
        return "consent or bot-challenge URL"
    if (item.get("text_chars") or 0) < min_chars:
        return f"extracted text below {min_chars} chars"
    return None


def run_candidate_lane(
    session: Session,
    config: SourcesConfig,
    *,
    limit: int = 3,
    min_chars: int = 1500,
) -> LaneResult:
    """Validate discovered candidates by acquiring them and storing non-canonical evidence.

    Candidates are promoted to evidence only when the page returns 200, is
    robots-allowed (the shared robots gate enforces this and reports
    `blocked`/`robots_denied` otherwise) and yields substantive text. They
    stay marked `is_candidate=True` until a human/validation step marks
    them canonical.
    """

    from .models import DiscoveredCandidate

    result = LaneResult(lane="candidate")
    candidates = candidate_urls(session, limit=limit)
    if not candidates:
        return result
    result.sources_attempted = len(candidates)

    jobs = [
        {
            "id": cand.id,
            "url": cand.canonical_url,
            "fetch_url": cand.canonical_url,
            "fetch_mode": "http",
            "publisher": cand.host,
            "source_class": cand.source_class_guess or "editorial_discovery",
            "topics": cand.topics or [],
            "region": None,
            "language": None,
            "limit": 1,
        }
        for cand in candidates
    ]
    sinks = run_registry_lane_jobs(jobs)
    statuses = {s.get("source_id"): s for s in sinks.statuses}

    created = 0
    for item in sinks.items:
        cand = session.get(DiscoveredCandidate, item["source_id"])
        if cand is None:
            continue
        reason = _is_low_quality(item, min_chars=min_chars)
        if reason is not None:
            cand.validation_status = "rejected_low_quality"
            cand.validation_notes = reason
            continue
        item = dict(item)
        item["candidate_id"] = cand.id
        item["is_candidate"] = True
        item["validation_status"] = "unvalidated"
        item["source_id"] = None
        created += store_articles(session, [item])
        cand.validation_status = "evidence_captured"
        cand.validation_notes = f"captured as evidence {item['capture_hash'][:12]}"
    for cand_id, status in statuses.items():
        cand = session.get(DiscoveredCandidate, cand_id)
        if cand is not None and status.get("status") != "ok":
            cand.validation_notes = status.get("error") or status.get("status")
    result.items_new = created
    result.statuses = list(statuses.values())
    return result
