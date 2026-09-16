"""Thin runner that executes the Scrapy spiders with the shared transport policy.

All politeness/robots/retry behaviour comes from Scrapy middleware via
scrapy_settings(). This module only builds job payloads, collects the spider
results through a result sink, and starts one reactor run per call.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from scrapy.crawler import CrawlerProcess

from .adapters.bing_news import bing_news_url
from .adapters.gdelt import gdelt_url
from .registry import SourcesConfig
from .scrapy_settings import scrapy_settings
from .spiders import AcquisitionSpider, DiscoverySpider


def build_source_jobs(
    config: SourcesConfig, *, source_ids: list[str] | None = None, limit: int | None = None
) -> list[dict]:
    jobs: list[dict] = []
    for cfg in config.enabled_sources():
        if source_ids and cfg.id not in source_ids:
            continue
        if cfg.fetch is None and not source_ids:
            continue  # only verified fetch plans join the scheduled lane
        mode = cfg.fetch.mode if cfg.fetch else cfg.preferred_fetch
        fetch_url = cfg.fetch.url if cfg.fetch and cfg.fetch.url else cfg.url
        parts = urlsplit(fetch_url)
        jobs.append(
            {
                "id": cfg.id,
                "url": cfg.url,
                "fetch_url": fetch_url,
                "fetch_mode": mode,
                "robots_url": f"{parts.scheme}://{parts.netloc}/robots.txt",
                "publisher": cfg.publisher,
                "source_class": cfg.source_class,
                "topics": cfg.topics,
                "region": cfg.region,
                "language": cfg.language,
                "limit": (cfg.fetch.limit if cfg.fetch and cfg.fetch.limit else 5),
            }
        )
    return jobs


def build_query_jobs(config: SourcesConfig, *, providers: list[str] | None = None) -> list[dict]:
    jobs: list[dict] = []
    for query in config.discovery_queries:
        if not query.enabled or (providers and query.provider not in providers):
            continue
        if query.provider == "gdelt":
            fetch_url = gdelt_url(query.query)
        elif query.provider == "bing_news":
            fetch_url = bing_news_url(query.query)
        else:
            fetch_url = query.query  # searxng: full endpoint URL lives in config
        jobs.append(
            {
                "id": query.id,
                "provider": query.provider,
                "query": query.query,
                "fetch_url": fetch_url,
                "class_hint": query.class_hint,
                "topics": query.topics,
            }
        )
    return jobs


def run_spiders(
    acquisition_jobs: list[dict] | None = None,
    discovery_jobs: list[dict] | None = None,
    *,
    obey_robots: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Run all jobs in one reactor cycle and return (acquisition_sinks, discovery_sinks)."""
    acquisition_jobs = acquisition_jobs or []
    discovery_jobs = discovery_jobs or []
    if not acquisition_jobs and not discovery_jobs:
        return [], []

    process = CrawlerProcess(settings=scrapy_settings(obey_robots=obey_robots))
    # One spider handles the whole lane; the spider keys results by source/query id.
    acq_sink_limit: dict = {}
    if acquisition_jobs:
        first = acquisition_jobs[0]
        process.crawl(
            AcquisitionSpider,
            job={
                "sources": acquisition_jobs,
                "limit": first.get("limit"),
                "result_sink": acq_sink_limit,
            },
        )
    disc_sink: dict = {}
    if discovery_jobs:
        process.crawl(DiscoverySpider, job={"queries": discovery_jobs, "result_sink": disc_sink})
    process.start()
    return ([acq_sink_limit] if acquisition_jobs else []), ([disc_sink] if discovery_jobs else [])


def run_acquisition(job: dict, *, obey_robots: bool = True) -> dict:
    sinks, _ = run_spiders([job], [], obey_robots=obey_robots)
    return sinks[0]


def run_discovery(job: dict, *, obey_robots: bool = True) -> dict:
    _, sinks = run_spiders([], [job], obey_robots=obey_robots)
    return sinks[0]
