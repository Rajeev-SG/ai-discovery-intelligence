# Ingestion and acquisition

How `config/sources.yaml` becomes normalised, provenance-bearing evidence.

## Adopted components (no bespoke plumbing)

| Job | Component | Where |
|---|---|---|
| Orchestration, schedules, run history, retries | **Dagster** | `src/ai_discovery/pipeline.py` |
| Crawling, robots, throttling, retries, redirects | **Scrapy** (2.19) | `src/ai_discovery/spiders.py`, `scrapy_settings.py` |
| Article/metadata extraction | **Trafilatura** (2.2) | `src/ai_discovery/acquisition/extract.py` |
| Change tripwire | **changedetection.io** | `docker-compose.yml` (`--profile tripwire`) |
| Persistence + migrations | **PostgreSQL + SQLAlchemy + Alembic** | `src/ai_discovery/models.py`, `alembic/` |
| API | **FastAPI** | `src/ai_discovery/api.py` |

There is **no** hand-written fetch engine. Robots enforcement, per-domain
throttling, retry and redirect handling are Scrapy middleware
(`RobotsTxtMiddleware`, `AutoThrottle`, `RetryMiddleware`, `RedirectMiddleware`).
Redirect targets re-enter the downloader, so per-URL robots policy still applies
after a redirect. `src/ai_discovery/*` contains domain glue only: which URLs
belong to a configured source, how a feed maps to article requests, and how a
page maps to an evidence row.

## Lanes

1. **Registry lane** — configured sources with a verified `fetch:` plan.
   Feed/API/static-HTTP fetch is preferred; browser rendering is a last resort
   and is not enabled in v1.
2. **Discovery lane** — configured `discovery_queries` (GDELT DOC API, Bing News
   RSS) find candidate URLs. Candidates are canonicalised, deduplicated and
   stored as **non-canonical** rows (`discovered_candidate`) until validated.
3. **Candidate lane** — a discovered candidate is fetched, gated on quality
   (consent/bot-challenge shells and thin text are rejected) and stored as
   evidence with `is_candidate = true` until a human promotes it.

Run locally:

```bash
uv sync --extra dev
docker compose up -d db
export AI_DISCOVERY_DATABASE_URL=postgresql+psycopg://ai_discovery:ai_discovery@127.0.0.1:55432/ai_discovery
uv run alembic upgrade head
uv run ai-discovery-ingest all --limit 3     # both lanes, one reactor cycle
uv run uvicorn ai_discovery.api:app --reload --port 8000
```

Dagster UI: `uv run dagster dev -m ai_discovery.pipeline` (assets
`source_registry`, `feed_items`, `discovered_urls`, `source_health`,
`coverage_gaps`; daily schedule `daily_acquisition`).

## Politeness and provenance rules

- `robots.txt` is fetched and classified per host before any source is fetched:
  `401/403` → `robots_denied` (never bypassed), `404/410` → allowed with no
  directives, unreachable/5xx → `blocked` and reported. Failures are stored in
  `source_check` and surfaced in `/sources`; nothing is silently dropped.
- Per-domain delay (`DOWNLOAD_DELAY`, `AutoThrottle`) is enforced process-wide.
- **Google News RSS is deliberately not used** — `news.google.com/robots.txt`
  disallows `/rss/search`. Bing News RSS is used instead, and its
  `apiclick.aspx?url=` redirect is unwrapped so the tracking URL is never stored.
- **GDELT DOC API** returns HTTP 429 under load; its queries run through Scrapy
  AutoThrottle with a 30-day window and are reported as lane failures when they
  do not complete.
- Raw HTML snapshots stay private on local disk, content-addressed by SHA-256
  (`var/snapshots/`). The API exposes metadata, an excerpt, the capture hash and
  the source link only; `/evidence` never returns `snapshot_path`.
- Evidence rows are append-only. A new capture is a new row keyed by
  `(canonical_url, capture_hash)`.

## Dates: published vs modified

`published_at`, `modified_at` and `observed_at` are separate fields.
`modified_at` is never presented as the publication date. This matters for living
pages: the Ahrefs "50 Most-Cited Websites in ChatGPT" page has
`datePublished = 2025-09-10` and `dateModified = 2026-09-02`; the capture hash
makes each monthly snapshot auditable without rewriting the original date.

## Storage added for issue #3

Extracted plain text is persisted privately by capture hash
(`var/snapshots/text/<capture_hash>.txt`, `snapshot_store.store_extracted_text`),
so the claim ledger (#3) can re-read the exact text behind any `capture_hash`
without re-fetching a living page.

## API (read-only)

- `GET /evidence?limit=100` → `{items:[{id,url,title,publisher,source_class,published_at,modified_at,observed_at,topics,capture_hash,excerpt,validation_status,is_candidate}],total}`
  (plus `source_id`, `region`, `language`, `http_status`, `extractor`,
  `snapshot_available`). Filters: `source_class`, `publisher`, `topic`, `q`,
  `include_candidates`, `limit`, `offset`.
- `GET /sources` → source registry + health (`health_status`, `last_success_at`,
  `last_http_status`, `consecutive_failures`, `last_error`).
- `GET /sources/{id}/checks` → health/staleness history.
- `GET /candidates` → non-canonical discovery candidates (unvalidated by
  default; `?include_registry=true` to include registry-host matches).
- `GET /health` → counts for evidence, sources, degraded sources, candidates.

Raw snapshots and `snapshot_path` are never exposed.

## Adding a source

1. Add the entry to `config/sources.yaml` with `class`, `topics` and a `fetch:`
   block (`mode`, `url`, `verified_at`). Verify the feed/endpoint returns real
   content first and record that date.
2. Keep `preferred_fetch` honest (`rss`, `api`, `sitemap`, `http`).
3. Run `ai-discovery-ingest registry --source <id>` and check `/sources`.

## Not yet covered

- `scrapy-playwright` JS fallback is declared in the adopted stack but no source
  currently requires it (all configured sources return usable content over HTTP).
- RSSHub and SearXNG are not deployed; no configured source uses a feedless
  route yet. Add them (pinned) in the change that first configures a consumer.
- GDELT results depend on API availability; no retry-backoff beyond Scrapy's
  retry middleware is configured.
