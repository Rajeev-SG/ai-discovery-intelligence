"""Scrapy spiders — the only transport path for the registry and discovery lanes.

Generic work belongs to middleware: RobotsTxtMiddleware (per-URL + redirect
targets), AutoThrottle, RetryMiddleware, RedirectMiddleware, HttpErrorMiddleware.
These spiders only contain domain glue: which URLs belong to a configured source,
how a feed maps to article requests, and how a page maps to an evidence item.
"""

from __future__ import annotations

import datetime as dt

import scrapy

from .acquisition.extract import extract_document
from .adapters.feed import parse_feed
from .hashing import canonicalise_url, normalise_text, sha256_text
from .snapshot_store import store_extracted_text, store_snapshot

ALLOW = "allow"
DENY = "deny"  # 401/403 — access control, never bypassed
UNKNOWN = "unknown"  # unreachable / 5xx — surfaced, never crawled
NO_DIRECTIVES = {404, 410}  # standard "no rules published"


def _iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


class AcquisitionSpider(scrapy.Spider):
    """Fetch configured sources and their feed entries; emit normalised evidence."""

    name = "ai_discovery_acquisition"

    def __init__(self, job: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.sources: list[dict] = job.get("sources", [])
        self.limit: int | None = job.get("limit")
        self.sink: dict = job.setdefault("result_sink", {})
        self.robots_state: dict[str, str] = {}
        self.items_emitted: dict[str, int] = {}

    @property
    def statuses(self) -> list[dict]:
        return self.sink.setdefault("statuses", [])

    async def start(self):
        # Scrapy >=2.13 consumes Spider.start(); keep the synchronous
        # start_requests() domain logic and delegate to it here.
        for request in self.start_requests():
            yield request

    def start_requests(self):
        by_host: dict[str, list[dict]] = {}
        for source in self.sources:
            by_host.setdefault(source["robots_url"], []).append(source)
        for robots_url, sources in by_host.items():
            yield scrapy.Request(
                robots_url,
                callback=self.parse_robots,
                errback=self.robots_unreachable,
                meta={"sources": sources, "dont_obey_robotstxt": True},
                dont_filter=True,
            )

    def parse_robots(self, response):
        sources = response.meta["sources"]
        if response.status in (401, 403):
            state = DENY
        elif response.status in NO_DIRECTIVES or 200 <= response.status < 300:
            state = ALLOW
        else:
            state = UNKNOWN
        for source in sources:
            self.robots_state[source["id"]] = state
        if state != ALLOW:
            for source in sources:
                self.statuses.append(
                    {
                        "kind": "source_status",
                        "source_id": source["id"],
                        "status": "robots_denied" if state == DENY else "blocked",
                        "error": f"robots.txt {state} ({response.status})",
                    }
                )
            return
        for source in sources:
            yield from self._source_requests(source)

    def robots_unreachable(self, failure):
        for source in failure.request.meta.get("sources", []):
            self.robots_state[source["id"]] = UNKNOWN
            self.statuses.append(
                {
                    "kind": "source_status",
                    "source_id": source["id"],
                    "status": "blocked",
                    "error": f"robots.txt unreachable: {failure.getErrorMessage()}",
                }
            )

    def _source_requests(self, source: dict):
        yield scrapy.Request(
            source["fetch_url"],
            callback=self.parse_source,
            errback=self.request_error,
            meta={"source": source},
        )

    def parse_source(self, response):
        source = response.meta["source"]
        if response.status >= 400:
            self.statuses.append(
                {
                    "kind": "source_status",
                    "source_id": source["id"],
                    "status": "error",
                    "http_status": response.status,
                    "error": f"HTTP {response.status}",
                }
            )
            return
        if source["fetch_mode"] in {"rss", "rsshub"}:
            entries = parse_feed(bytes(response.body), limit=self.limit or source.get("limit", 5))
            if not entries:
                self.statuses.append(
                    {
                        "kind": "source_status",
                        "source_id": source["id"],
                        "status": "empty",
                        "http_status": response.status,
                    }
                )
            for entry in entries:
                yield scrapy.Request(
                    entry.canonical_url or entry.url,
                    callback=self.parse_article,
                    errback=self.request_error,
                    meta={"source": source, "entry": entry.__dict__},
                )
            return
        yield self._emit(
            self._article_item(source, response, feed_published=None, feed_source=None)
        )

    def parse_article(self, response):
        source = response.meta["source"]
        entry = response.meta["entry"]
        published = entry.get("published_at")
        yield self._emit(
            self._article_item(
                source,
                response,
                feed_published=published,
                feed_source="feed" if published else None,
            )
        )

    def _emit(self, item: dict) -> dict:
        self.sink.setdefault("items", []).append(item)
        return item

    def _article_item(self, source, response, *, feed_published, feed_source):
        raw = bytes(response.body)
        html = raw.decode("utf-8", "replace")
        doc = extract_document(html, url=response.url, feed_published=feed_published)
        text = doc.text or ""
        raw_hash, snapshot_path = store_snapshot(raw, suffix=".html")
        capture_hash = sha256_text(normalise_text(text))
        store_extracted_text(capture_hash, text)
        self.items_emitted[source["id"]] = self.items_emitted.get(source["id"], 0) + 1
        return {
            "kind": "article",
            "source_id": source["id"],
            "url": response.url,
            "canonical_url": canonicalise_url(response.url),
            "title": doc.title,
            "publisher": source["publisher"],
            "source_class": source["source_class"],
            "topics": source["topics"],
            "language": doc.language or source.get("language"),
            "region": source.get("region"),
            "published_at": _iso(doc.published_at or feed_published),
            "published_at_source": doc.published_at_source or feed_source,
            "modified_at": _iso(doc.modified_at),
            "text": text,
            "excerpt": text[:600],
            "text_chars": len(text),
            "capture_hash": capture_hash,
            "raw_sha256": raw_hash,
            "snapshot_path": snapshot_path,
            "extractor": doc.extractor,
            "fetch_mode": source["fetch_mode"],
            "http_status": response.status,
            "content_type": response.headers.get(b"content-type", b"").decode("utf-8", "replace"),
            "etag": response.headers.get(b"etag", b"").decode("utf-8", "replace") or None,
            "http_last_modified": (
                response.headers.get(b"last-modified", b"").decode("utf-8", "replace") or None
            ),
            "observed_at": dt.datetime.now(dt.UTC).isoformat(),
        }

    def request_error(self, failure):
        source = failure.request.meta.get("source", {})
        self.statuses.append(
            {
                "kind": "source_status",
                "source_id": source.get("id"),
                "status": "error",
                "error": failure.getErrorMessage(),
            }
        )

    def closed(self, reason):
        sink = self.sink
        sink["sources"] = self.sources
        seen = {s.get("source_id") for s in self.statuses}
        for source in self.sources:
            if source["id"] in self.items_emitted or source["id"] in seen:
                continue
            self.statuses.append(
                {
                    "kind": "source_status",
                    "source_id": source["id"],
                    "status": "empty",
                    "items_new": 0,
                }
            )
        for source_id, count in self.items_emitted.items():
            if source_id not in seen:
                self.statuses.append(
                    {
                        "kind": "source_status",
                        "source_id": source_id,
                        "status": "ok",
                        "items_new": count,
                    }
                )


class DiscoverySpider(scrapy.Spider):
    """Discovery lane: run configured open-source queries through Scrapy."""

    name = "ai_discovery_discovery"

    def __init__(self, job: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.queries: list[dict] = job.get("queries", [])
        self.max_results: int = job.get("max_per_query", 10)
        self.sink: dict = job.setdefault("result_sink", {})
        self._seen: set[str] = set()

    @property
    def hits(self) -> list[dict]:
        return self.sink.setdefault("candidates", [])

    @property
    def failures(self) -> list[dict]:
        return self.sink.setdefault("failures", [])

    async def start(self):
        # Scrapy >=2.13 consumes Spider.start(); keep the synchronous
        # start_requests() domain logic and delegate to it here.
        for request in self.start_requests():
            yield request

    def start_requests(self):
        for query in self.queries:
            yield scrapy.Request(
                query["fetch_url"],
                callback=self.parse_query,
                errback=self.query_error,
                meta={"query": query},
                dont_filter=True,
            )

    def parse_query(self, response):
        query = response.meta["query"]
        if response.status >= 400:
            self.failures.append(
                {
                    "query_id": query["id"],
                    "provider": query["provider"],
                    "error": f"HTTP {response.status}",
                }
            )
            return
        try:
            hits = parse_provider(query, bytes(response.body))
        except Exception as exc:  # surfaced, never silently dropped
            self.failures.append(
                {"query_id": query["id"], "provider": query["provider"], "error": str(exc)}
            )
            return
        for hit in hits[: self.max_results]:
            if hit.canonical_url in self._seen:
                continue
            self._seen.add(hit.canonical_url)
            self.hits.append(
                {
                    "kind": "candidate",
                    "url": hit.url,
                    "canonical_url": hit.canonical_url,
                    "title": hit.title,
                    "host": hit.domain,
                    "provider": hit.provider,
                    "query": hit.query,
                    "published_at": _iso(hit.published_at),
                    "source_class_guess": query.get("class_hint"),
                    "topics": query.get("topics", []),
                }
            )

    def query_error(self, failure):
        query = failure.request.meta.get("query", {})
        self.failures.append(
            {
                "query_id": query.get("id"),
                "provider": query.get("provider"),
                "error": failure.getErrorMessage(),
            }
        )


def parse_provider(query: dict, body: bytes):
    """Map a raw provider payload to DiscoveryHit rows (domain glue only)."""
    import json

    from .adapters.bing_news import parse_bing_news
    from .adapters.gdelt import parse_gdelt
    from .adapters.searxng import parse_searxng

    provider = query["provider"]
    if provider == "gdelt":
        return parse_gdelt(json.loads(body.decode("utf-8", "replace")), query=query["query"])
    if provider == "bing_news":
        return parse_bing_news(body, query=query["query"])
    if provider == "searxng":
        return parse_searxng(json.loads(body.decode("utf-8", "replace")), query=query["query"])
    raise ValueError(f"unsupported discovery provider: {provider}")
