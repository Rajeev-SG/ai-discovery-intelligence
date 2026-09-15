# 02 — Ingest the free source catalogue with mature OSS, not bespoke plumbing

## Outcome
Turn `config/sources.yaml` into a working source acquisition layer and visible evidence feed.

## Adopted stack
Dagster assets/schedules; Scrapy for crawling; Trafilatura for extraction; Playwright/scrapy-playwright only for JS-required pages; RSSHub where a mature route exists; changedetection.io as change tripwire. Do not build equivalents.

## Requirements
- Treat sources as configured assets with source class, fetch mode, topics, URL, last success, content hash, HTTP metadata and health.
- Prefer official RSS/API/sitemap/static HTTP over browser rendering.
- Respect robots/terms/rate limits. Store only evidence needed for audit; raw snapshots remain private.
- Seed live adapters for at least one official source, Similarweb, Peec, Ahrefs or Semrush, SISTRIX, and one regional/China source.
- Add a **discovery lane** that uses configured open/free discovery sources (GDELT, Google News RSS, RSSHub and/or SearXNG as appropriate) to find candidate URLs that are not yet in the curated registry. Deduplicate/canonicalise candidates and keep them non-canonical until validated.
- Surface failures/staleness rather than silently dropping them.
- Dagster should orchestrate source assets; changedetection.io should trigger targeted refresh, not become the canonical database.

## Real product proof required
Ingest at least **six live free sources spanning four source classes**, then render an evidence-feed page showing title, publisher, publication/observed date, source class, topics, capture hash and link. Include at least one current 2026 report with a substantive AI-discovery finding **and one newly discovered candidate URL that was not a hard-coded source-registry entry**.

## Done when
A reviewer can click the evidence feed and see real public evidence that has been acquired and normalised. “Crawler runs” or a Dagster graph alone is insufficient.
