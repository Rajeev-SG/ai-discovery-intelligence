# Source collection strategy

## Baseline before monitoring

1. Establish the global surface registry.
2. For each surface, discover official docs and high-value public research sources.
3. Capture a baseline snapshot and metadata.
4. Extract claims and methodology.
5. Normalize into the canonical schema.
6. Only then monitor for changes/new evidence.

## Collection priority

1. RSS/Atom if available.
2. Documented JSON/API/feed endpoint.
3. Sitemap discovery + normal HTTP.
4. Static HTML.
5. JS rendering only where required.
6. Search/news discovery feeds for unknown new reports.

## OSS responsibilities

- RSSHub bridges public sources without feeds when an existing route fits.
- changedetection.io watches known high-value pages and feeds.
- Scrapy performs controlled discovery/crawl.
- Trafilatura extracts main content and metadata.
- Playwright is a narrow JS fallback.
- Dagster owns asset dependencies, schedules, retries and run history.

## No-source-copy principle

Raw captures remain private. The product stores normalized claims, short excerpts where legally appropriate, hashes, URLs, publication/capture dates and methodology — not republished full articles.
