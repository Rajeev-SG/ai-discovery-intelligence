# Adopted OSS stack

This document is authoritative for v1. Coding agents should use these components rather than reopen a tool bake-off unless a concrete requirement is unmet.

| Job | Adopt | Why | Do not build |
|---|---|---|---|
| Data/workflow orchestration | **Dagster OSS** | Apache-2.0; mature; schedules, retries, assets, lineage and UI | cron orchestration, custom job dashboard, home-grown retry engine |
| Change detection | **changedetection.io** | mature self-hosted watcher, selectors, notifications, browser support | HTML diff scheduler/history service |
| Crawling/discovery | **Scrapy** | long-lived, mature Python crawler; 2.19 current in Sep 2026 | custom async crawler framework |
| Article/page extraction | **Trafilatura** | mature extraction + metadata; current 2.2 | bespoke boilerplate removal/readability engine |
| JS rendering fallback | **Playwright + scrapy-playwright** | active, reliable; only when HTTP fetch fails | custom browser automation wrapper |
| Feed generation for feedless sites | **RSSHub** | established self-hosted feed generator | per-site polling/feed emulation where an RSSHub route exists |
| Supplemental meta-search discovery | **SearXNG** | mature self-hosted metasearch; discovery signal only | custom multi-search-engine scraper |
| Database | **PostgreSQL** | durable relational history/provenance | bespoke document database |
| Schema/migrations | **SQLAlchemy + Alembic + Pydantic** | mature Python standards | custom ORM/migration layer |
| Structured prose extraction | **Instructor + Pydantic via OpenRouter-compatible endpoint** | mature schema validation/retry plumbing; model is configurable | hand-written JSON parsing/retry loops |
| API | **FastAPI** | mature typed Python API framework | custom HTTP server |
| Web app | **Next.js App Router** | established React full-stack framework | custom SPA/toolchain |
| Observation grid | **TanStack Table v9 + TanStack Virtual** | MIT; stable v9; sorting/filtering/faceting/expansion/virtualisation; strong React fit | table/grid mechanics |
| Accessible UI primitives | **Radix UI / shadcn/ui composition** | established accessible primitives | modal, sheet, dropdown, tooltip primitives |
| Full-text search v1 | **PostgreSQL FTS + pg_trgm** | enough for expected corpus, zero extra service | Elasticsearch/Meilisearch unless proven necessary |
| Tests | **pytest + Playwright** | backend + browser E2E | bespoke test harness |
| Dependency updates | **Renovate** | automated dependency PRs | custom dependency checker |

## Explicit non-selections for v1

- **AG Grid:** excellent grid, but master/detail expansion is Enterprise-only; avoid a licence trap for a free/self-hosted v1.
- **Tabulator:** strong MIT alternative and viable fallback, but TanStack Table is the chosen React-native baseline. Do not run a bake-off.
- **Firecrawl/Crawl4AI:** useful projects, but the mature Scrapy + Trafilatura + Playwright path is simpler, less coupled to LLM workflows and adequate for this source corpus.
- **Airflow/Temporal:** more infrastructure than this project needs. Dagster already solves the job.
- **n8n:** useful automation product but less appropriate than Dagster for lineage-heavy source/evidence assets; also avoid mixing orchestration paradigms.
- **vector DB / Elasticsearch:** no demonstrated v1 need.

## Evidence checked 2026-09-15

- Dagster remains Apache-2.0 and actively released.
- Scrapy 2.19 released 2026-09-10.
- Trafilatura 2.2 released 2026-07-31.
- Playwright stable 1.62.x released July 2026.
- `scrapy-playwright` 0.0.48 released 2026-07-10.
- TanStack Table v9 reached stable release in August 2026 and remains MIT.
- changedetection.io remains actively maintained in 2026.
