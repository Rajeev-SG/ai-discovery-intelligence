"""Regression tests for the two coverage bugs found by the #48 funnel audit.

1. The acquisition lane built jobs only for sources with a hand-written
   ``fetch:`` block, silently skipping every source that relied on
   ``preferred_fetch``. On the 2026-09-19 production run only 12 of 51 configured
   sources were ever attempted. ``build_source_jobs`` must now return a job for
   every enabled source, with the mode resolved from the config.

2. ``/claims?surface=`` returned HTTP 500 on PostgreSQL because the JSONB
   containment filter compared ``jsonb @> varchar``. It must return the surface's
   claims.
"""

from __future__ import annotations

from ai_discovery.crawler import build_source_jobs
from ai_discovery.registry import load_sources_config


def test_every_enabled_source_joins_the_acquisition_lane():
    """No enabled source is silently dropped for lacking a verified fetch block."""

    config = load_sources_config()
    jobs = build_source_jobs(config)
    enabled = {s.id for s in config.enabled_sources()}
    assert {j["id"] for j in jobs} == enabled
    assert len(jobs) == len(enabled)


def test_jobs_carry_a_concrete_resolved_fetch_mode():
    """Each job has a usable mode and URL even without a hand-written fetch block."""

    config = load_sources_config()
    unverified = [s for s in config.enabled_sources() if s.fetch is None]
    assert unverified, "expected sources relying on preferred_fetch"
    for job in build_source_jobs(config):
        assert job["fetch_mode"], job
        assert job["fetch_url"], job
        assert job["fetch_mode"] in {
            "api", "rss", "rsshub", "sitemap", "http", "browser"
        }, job


def test_source_id_filter_still_narrows_the_lane():
    config = load_sources_config()
    target = config.enabled_sources()[0].id
    jobs = build_source_jobs(config, source_ids=[target])
    assert [j["id"] for j in jobs] == [target]
