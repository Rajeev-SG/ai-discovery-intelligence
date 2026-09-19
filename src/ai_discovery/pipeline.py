"""Dagster definitions: capture → extraction assets, schedules and lineage.

Dagster owns scheduling, retries and run history. Assets call the domain
modules directly: the capture lane (crawler.py) renders and snapshots new
evidence; the extraction lane (semantic.py + claim_extract.py) turns changed
cleaned snapshots into quote-verified ledger claims.
"""

from __future__ import annotations

import datetime as dt

from dagster import (
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

from .claim_pipeline import extract_pending_claims
from .db import session_scope
from .ingest import run_discovery_lane, run_registry_lane, upsert_sources
from .models import EvidenceItem, Source, SourceCheck
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
    description="Crawl4AI/HTTP capture of configured free sources into hash-addressed snapshots.",
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
    group_name="claims",
    deps=[feed_items],
    description="Instructor + OpenRouter extraction: changed snapshots → quote-verified ledger claims.",
)
def claims(context) -> dict:
    with session_scope() as session:
        run = extract_pending_claims(session)
    context.add_asset_metadata({"claims_created": run.claims_created})
    return run.as_dict()


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
    from sqlalchemy import func, select

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


# --- Schedules (docs/PIPELINES.md) ----------------------------------------- #

acquisition_job = define_asset_job("acquisition_job", selection="*")
discovery_job = define_asset_job("discovery_job", selection=["source_registry", "discovered_urls", "source_health", "coverage_gaps"])
audit_job = define_asset_job("coverage_audit_job", selection=["source_registry", "source_health", "coverage_gaps"])

daily_high_value = ScheduleDefinition(
    name="daily_high_value_sources", job=acquisition_job, cron_schedule="0 6 * * *"
)
weekly_discovery = ScheduleDefinition(
    name="weekly_discovery_lane", job=discovery_job, cron_schedule="0 7 * * 1"
)
weekly_coverage_audit = ScheduleDefinition(
    name="weekly_coverage_audit", job=audit_job, cron_schedule="0 8 * * 1"
)

defs = Definitions(
    assets=[
        source_registry,
        feed_items,
        claims,
        discovered_urls,
        source_health,
        coverage_gaps,
    ],
    jobs=[acquisition_job, discovery_job, audit_job],
    schedules=[daily_high_value, weekly_discovery, weekly_coverage_audit],
)
