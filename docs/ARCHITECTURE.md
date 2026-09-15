# Architecture

## Core principle

Use mature OSS for generic platform work; keep custom code concentrated in AI-discovery semantics.

```text
        FREE SOURCE / DISCOVERY PLANE
 official docs · RSS · sitemaps · vendor research
 Similarweb/Peec/etc free blogs · GDELT · Google News RSS
 arXiv/OpenAlex · regional research · specialist press
                         |
            RSSHub / Scrapy / HTTP discovery
                         |
                  changedetection.io
                         |
              changed source / new source
                         |
          Scrapy + Trafilatura (+ Playwright fallback)
                         |
             immutable private evidence snapshot
                         |
                structured claim extraction
                         |
             deterministic schema validation
                         |
                 canonical PostgreSQL
               /          |            \
          evidence      claims        events
               \          |            /
                confidence + significance
                         |
           +-------------+--------------+
           |                            |
  OBSERVATION PLANE                EXEC LAYER
 Next.js + TanStack Table          weekly brief
 search/filter/expand              living POV
 evidence history                  changelog
```

## Workflow/orchestration

Dagster OSS owns schedules, assets, retries, lineage and pipeline observability. Do not build a home-grown scheduler/queue/workflow status UI.

## Storage

PostgreSQL is canonical. Raw evidence snapshots are content-addressed private files with hashes and DB metadata in v1. Do not add Elasticsearch, a vector database, Kafka or object-storage infrastructure until a demonstrated requirement exists.

## Acquisition

Prefer normal HTTP/RSS/sitemaps. Use Scrapy for crawling and source discovery, Trafilatura for article/content extraction, and Playwright through `scrapy-playwright` only for pages that genuinely require JavaScript.

## Change detection

`changedetection.io` is a tripwire. It does not become the canonical store.

## Frontend

Next.js App Router + stable TanStack Table v9 + TanStack Virtual + established accessible UI primitives. Do not implement sorting, filtering, faceting, pagination, row expansion or virtualisation from scratch.
