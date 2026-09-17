"""Registry/candidate lane transport: HTTP + Crawl4AI render fallback.

The rebuild replaces the Scrapy transport with two explicit steps:
1. a shared robots.txt gate (``ai_discovery.robots``) that fetches robots
   with the project UA and honours real directives — no misread 403 bodies;
2. a plain HTTP fetch for the source URL, with Crawl4AI rendering reserved
   for the JS-heavy sources that plain HTTP cannot read.

Both steps are injectable for tests; production builds one shared
``RenderClient`` so a whole run uses one browser instance.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import httpx

from .acquisition.extract import extract_document
from .hashing import canonicalise_url, normalise_text, sha256_text
from .render import RenderClient
from .robots import DENY, UNKNOWN, can_fetch, robots_policy
from .snapshot_store import snapshot_dir, store_extracted_text, store_snapshot


@dataclass
class FetchOutcome:
    """One transport attempt: item (when fetched) or status (when not)."""

    item: dict | None = None
    status: dict | None = None


@dataclass
class LaneSinks:
    """Structured output of one lane run."""

    items: list[dict] = field(default_factory=list)
    statuses: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)


def build_source_jobs(
    config,
    *,
    source_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Build acquisition jobs from the verified fetch plans in config."""
    jobs: list[dict] = []
    for cfg in config.enabled_sources():
        if source_ids and cfg.id not in source_ids:
            continue
        if cfg.fetch is None and not source_ids:
            continue  # only verified fetch plans join the scheduled lane
        mode = cfg.fetch.mode if cfg.fetch else cfg.preferred_fetch
        fetch_url = cfg.fetch.url if cfg.fetch and cfg.fetch.url else cfg.url
        jobs.append(
            {
                "id": cfg.id,
                "url": cfg.url,
                "fetch_url": fetch_url,
                "fetch_mode": mode,
                "publisher": cfg.publisher,
                "source_class": cfg.source_class,
                "topics": cfg.topics,
                "region": cfg.region,
                "language": cfg.language,
                "limit": (cfg.fetch.limit if cfg.fetch and cfg.fetch.limit else 5),
            }
        )
    return jobs


def build_query_jobs(config, *, providers: list[str] | None = None) -> list[dict]:
    """Discovery-lane job payloads (GDELT / Bing News endpoints)."""
    from .adapters.bing_news import bing_news_url
    from .adapters.gdelt import gdelt_url

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


def fetch_source(
    job: dict,
    *,
    client: httpx.Client | None = None,
    renderer: RenderClient | None = None,
    min_chars: int = 400,
) -> FetchOutcome:
    """One source: robots gate → HTTP → item (render fallback only when needed).

    The article parser (Trafilatura via acquisition.extract) stays the
    adopted extraction step; Crawl4AI is the JS-render fallback for pages
    whose plain HTTP body is a JS shell.
    """
    status = {"kind": "source_status", "source_id": job["id"]}
    state, parser = robots_policy(job["fetch_url"], client=client)
    if state == DENY:
        return FetchOutcome(status={**status, "status": "robots_denied", "error": "robots.txt deny"})
    if state == UNKNOWN:
        return FetchOutcome(status={**status, "status": "blocked", "error": "robots.txt unreachable"})
    # Parser is present for ALLOW (404/410 or directives). If directives exist and
    # forbid this URL, we stop — never bypass.
    if parser is not None and not can_fetch(job["fetch_url"], parser):
        return FetchOutcome(status={**status, "status": "robots_denied", "error": "robots directive"})
    owned_http = client is None
    http_client = client or httpx.Client(timeout=25, follow_redirects=True)
    try:
        response = http_client.get(job["fetch_url"])
    except (httpx.HTTPError, OSError) as error:
        return FetchOutcome(status={**status, "status": "error", "error": str(error)})
    finally:
        if owned_http:
            http_client.close()
    if response.status_code >= 400:
        return FetchOutcome(
            status={**status, "status": "error", "http_status": response.status_code,
                    "error": f"HTTP {response.status_code}"}
        )
    html = response.text
    doc = extract_document(html, url=str(response.url))
    if len(doc.text or "") < min_chars and renderer is not None:
        try:
            render = renderer.fetch(job["fetch_url"])
        except Exception as error:  # noqa: BLE001 — surfaced per-source, never fatal
            return FetchOutcome(
                status={**status, "status": "error", "error": f"render fallback failed: {error}"}
            )
        return FetchOutcome(item=_rendered_item(job, render))
    if len(doc.text or "") < min_chars:
        return FetchOutcome(
            status={**status, "status": "empty", "http_status": response.status_code,
                    "error": f"extracted text below {min_chars} chars"}
        )
    return FetchOutcome(item=_http_item(job, response, doc))


def _store_item_text(raw: bytes, text: str) -> tuple[str, str, str]:
    raw_hash, path = store_snapshot(raw, suffix=".html")
    capture_hash = sha256_text(normalise_text(text))
    store_extracted_text(capture_hash, text)
    return raw_hash, capture_hash, path


def _http_item(job: dict, response: httpx.Response, doc) -> dict:
    raw = response.content
    text = doc.text or ""
    raw_hash, capture_hash, path = _store_item_text(raw, text)
    return {
        "kind": "article",
        "source_id": job["id"],
        "url": str(response.url),
        "canonical_url": canonicalise_url(str(response.url)),
        "title": doc.title,
        "publisher": job["publisher"],
        "source_class": job["source_class"],
        "topics": job["topics"],
        "language": doc.language or job.get("language"),
        "region": job.get("region"),
        "published_at": _iso(doc.published_at),
        "published_at_source": doc.published_at_source,
        "modified_at": _iso(doc.modified_at),
        "text": text,
        "excerpt": text[:600],
        "text_chars": len(text),
        "capture_hash": capture_hash,
        "raw_sha256": raw_hash,
        "snapshot_path": path,
        "extractor": doc.extractor,
        "fetch_mode": job["fetch_mode"],
        "http_status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "observed_at": dt.datetime.now(dt.UTC).isoformat(),
    }


def _rendered_item(job: dict, render) -> dict:
    """Build the evidence item from a Crawl4AI render (raw + cleaned Markdown)."""
    text = render.cleaned_markdown.decode("utf-8", "replace")
    raw_hash, _ = None, None
    from .hashing import sha256_bytes

    raw_hash = sha256_bytes(render.raw_html)
    capture_hash = sha256_text(normalise_text(text))
    base = snapshot_dir()
    base.mkdir(parents=True, exist_ok=True)
    raw_path = base / f"{job['id']}-{raw_hash}.html"
    raw_path.write_bytes(render.raw_html)
    cleaned_path = base / f"{job['id']}-{capture_hash}.md"
    cleaned_path.write_bytes(render.cleaned_markdown)
    return {
        "kind": "article",
        "source_id": job["id"],
        "url": render.url,
        "canonical_url": canonicalise_url(render.url),
        "title": (render.cleaned_markdown.decode("utf-8", "replace").split("\n")[0].lstrip("# ")[:120]
                  or render.url),
        "publisher": job["publisher"],
        "source_class": job["source_class"],
        "topics": job["topics"],
        "language": job.get("language"),
        "region": job.get("region"),
        "published_at": None,
        "modified_at": None,
        "text": text,
        "excerpt": text[:600],
        "text_chars": len(text),
        "capture_hash": capture_hash,
        "raw_sha256": raw_hash,
        "snapshot_path": str(raw_path),
        "extractor": "crawl4ai",
        "fetch_mode": job["fetch_mode"],
        "http_status": render.http_status,
        "content_type": "text/markdown",
        "observed_at": dt.datetime.now(dt.UTC).isoformat(),
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def run_registry_lane_jobs(
    jobs: list[dict],
    *,
    client: httpx.Client | None = None,
    renderer: RenderClient | None = None,
    min_chars: int = 400,
) -> LaneSinks:
    """Run acquisition jobs sequentially; one client, one browser for a run."""
    sinks = LaneSinks()
    owned = client is None
    client = client or httpx.Client(timeout=25, follow_redirects=True)
    try:
        for job in jobs:
            outcome = fetch_source(job, client=client, renderer=renderer, min_chars=min_chars)
            if outcome.item:
                sinks.items.append(outcome.item)
                sinks.statuses.append(
                    {
                        "kind": "source_status",
                        "source_id": job["id"],
                        "status": "ok",
                        "http_status": outcome.item.get("http_status"),
                        "items_new": 1,
                    }
                )
            elif outcome.status:
                sinks.statuses.append(outcome.status)
    finally:
        if owned:
            client.close()
    return sinks


def run_discovery_jobs(jobs: list[dict]) -> LaneSinks:
    """Discovery lane: fetch each configured provider endpoint and parse hits."""
    from .spiders_parse import parse_provider

    sinks = LaneSinks()
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for job in jobs:
            try:
                response = client.get(job["fetch_url"])
            except (httpx.HTTPError, OSError) as error:
                sinks.failures.append(
                    {
                        "query_id": job["id"],
                        "provider": job["provider"],
                        "error": str(error),
                    }
                )
                continue
            if response.status_code >= 400:
                sinks.failures.append(
                    {
                        "query_id": job["id"],
                        "provider": job["provider"],
                        "error": f"HTTP {response.status_code}",
                    }
                )
                continue
            try:
                hits = parse_provider(job, response.content)
            except Exception as exc:  # noqa: BLE001 — surfaced, never silently dropped
                sinks.failures.append(
                    {"query_id": job["id"], "provider": job["provider"], "error": str(exc)}
                )
                continue
            seen: set[str] = set()
            for hit in hits[: job.get("max_results", 10)]:
                if hit.canonical_url in seen:
                    continue
                seen.add(hit.canonical_url)
                sinks.candidates.append(
                    {
                        "kind": "candidate",
                        "url": hit.url,
                        "canonical_url": hit.canonical_url,
                        "title": hit.title,
                        "host": hit.domain,
                        "provider": hit.provider,
                        "query": hit.query,
                        "published_at": _iso(hit.published_at),
                        "source_class_guess": job.get("class_hint"),
                        "topics": job.get("topics", []),
                    }
                )
    return sinks
