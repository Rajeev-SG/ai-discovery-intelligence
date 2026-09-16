"""Dagster definitions: source assets, schedules and lineage.

Dagster owns scheduling, retries and run history — no custom scheduler or run
dashboard exists in this repo. Assets call the domain modules in ingest.py /
discovery.py.
"""

from __future__ import annotations

from dagster import (
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

from .db import session_scope
from .ingest import run_discovery_lane, run_registry_lane, upsert_sources
from .models import Source, SourceCheck
from .registry import load_sources_config


@asset(group_name="registry", description="Mirrors config/sources.yaml into the source table.")
def source_registry(context) -> dict:
    config = load_sources_config()
    with session_scope() as session:
        sources = upsert_sources(session, config)
        context.add_asset_metadata({"sources": len(sources)})
        return {"sources": len(sources)}


@asset(
    group_name="acquisition",
    deps=[source_registry],
    description="Acquires configured free sources via Scrapy + Trafilatura.",
)
def feed_items(context) -> dict:
    config = load_sources_config()
    with session_scope() as session:
        result = run_registry_lane(session, config)
        context.add_asset_metadata(
            {"sources_attempted": result.sources_attempted, "items_new": result.items_new}
        )
        return result.as_dict()


@asset(
    group_name="discovery",
    deps=[source_registry],
    description="Discovers candidate URLs not yet in the curated registry.",
)
def discovered_urls(context) -> dict:
    config = load_sources_config()
    with session_scope() as session:
        result = run_discovery_lane(session, config)
        context.add_asset_metadata({"candidates_new": result.candidates_new})
        return result.as_dict()


@asset(
    group_name="health",
    deps=[feed_items, discovered_urls],
    description="Source health + staleness, surfaced rather than silently dropped.",
)
def source_health(context) -> dict:
    config = load_sources_config()
    from sqlalchemy import select

    with session_scope() as session:
        sources = list(session.scalars(select(Source)).all())
        degraded = []
        for source in sources:
            if source.enabled and (source.health_status != "ok" or source.last_success_at is None):
                degraded.append(
                    {
                        "source_id": source.id,
                        "health_status": source.health_status,
                        "last_success_at": (
                            source.last_success_at.isoformat() if source.last_success_at else None
                        ),
                        "consecutive_failures": source.consecutive_failures,
                        "last_error": source.last_error,
                    }
                )
        checks = session.scalar(select(SourceCheck).limit(1))
        payload = {
            "registered_sources": len(sources),
            "configured": len(config.enabled_sources()),
            "degraded": degraded,
            "has_check_history": checks is not None,
        }
        context.add_asset_metadata({"degraded_sources": len(degraded)})
        return payload


@asset(
    group_name="health",
    deps=[source_health],
    description="Coverage gaps: registry entries with no fresh evidence yet.",
)
def coverage_gaps(context) -> dict:
    import datetime as dt

    from sqlalchemy import func, select

    from .models import EvidenceItem

    with session_scope() as session:
        counts = dict(
            session.execute(
                select(EvidenceItem.source_id, func.count()).group_by(EvidenceItem.source_id)
            ).all()
        )
        classes = dict(
            session.execute(
                select(EvidenceItem.source_class, func.count()).group_by(EvidenceItem.source_class)
            ).all()
        )
    config = load_sources_config()
    gaps = [s.id for s in config.enabled_sources() if not counts.get(s.id)]
    payload = {
        "sources_with_evidence": len(counts),
        "evidence_by_class": classes,
        "registry_sources_without_evidence": gaps,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    context.add_asset_metadata({"sources_without_evidence": len(gaps)})
    return payload


acquisition_job = define_asset_job("acquisition_job", selection="*")
daily_schedule = ScheduleDefinition(
    name="daily_acquisition", job=acquisition_job, cron_schedule="0 6 * * *"
)

defs = Definitions(
    assets=[source_registry, feed_items, discovered_urls, source_health, coverage_gaps],
    jobs=[acquisition_job],
    schedules=[daily_schedule],
)
