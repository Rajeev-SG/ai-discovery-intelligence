# Issue #2 — real product proof

Captured 2026-09-16 by running the registry, discovery and candidate lanes
against live public sources. Reproduce with `uv run ai-discovery-ingest all`
then `GET /evidence`.

## Machine-readable artefact

`docs/evidence/issue2_proof_2026-09-16.json` — full serialised API rows for the
run (evidence sample, sources with health, discovered candidates).

## Headline counts (from the run)

| Metric | Value |
|---|---|
| Evidence items | 41 |
| Distinct sources with evidence | 13 |
| Source classes covered | 4 (`official`, `market_telemetry`, `visibility_research`, `editorial_discovery`) |
| Discovered candidates (non-registry) | 20 |
| Candidates validated into evidence | 4 |

Requirement: ≥6 live sources across ≥4 classes. Met: 13 sources, 4 classes.

## Current 2026 report with a substantive AI-discovery finding

| Field | Value |
|---|---|
| Title | The 50 Most-Cited Websites in ChatGPT |
| Publisher | Ahrefs (visibility research) |
| URL | https://ahrefs.com/blog/most-cited-domains-in-chatgpt/ |
| published_at | 2025-09-10 (datePublished) |
| modified_at | 2026-09-02 (dateModified) |
| Captured | 2026-09-16, capture hash `…` (see artefact) |
| Finding | Reddit is the largest cited domain at 16.8% mention share, US all-topics, September 2026 snapshot. |

The Semrush/Promptwatch Reddit-citation article
(`https://www.semrush.com/blog/reddits-citations-in-chatgpt-fall/`,
`datePublished = 2026-08-26`, fixed not auto-updated) is also ingested. The two
are stored as separate evidence rows with their own capture hashes; the living
Ahrefs page keeps `published_at` distinct from `modified_at`.

## Newly discovered candidate (not a hard-coded registry entry)

The discovery lane ran `bing-news-ai-visibility` and
`bing-news-ai-referral-traffic` (Bing News RSS, robots-allowed) and stored 20
candidates on hosts that are **not** in `config/sources.yaml`, e.g.:

- `adweek.com` — "AI Search Levels Playing Field for Challenger Brands"
- `entrepreneur.com` — "An Online Seller's Guide to Increasing Visibility…"
- `mmm-online.com` — "Answer Engine Optimization: Why it matters for pharma…"

Four candidates passed the quality gate and were captured as evidence with
`is_candidate = true`, e.g. `hindustantimes.com` (8,756 chars) and
`entrepreneur.com` (7,953 chars). Consent/bot-challenge shells
(`finance.yahoo.com` "guce") were rejected, not stored.

## Source health and blockers (real, surfaced not dropped)

- All 13 configured-and-crawled sources returned HTTP 200.
- **Google News RSS is blocked by robots** (`news.google.com/robots.txt`
  disallows `/rss/search`). Replaced with Bing News RSS.
- **GDELT DOC API returns HTTP 429** when polled during this run; the lane
  reports it as a failure rather than silently dropping the query.

## How a reviewer can click the feed

```bash
docker compose up -d db && uv run alembic upgrade head
uv run ai-discovery-ingest all --limit 3
uv run uvicorn ai_discovery.api:app --port 8000
curl 'http://127.0.0.1:8000/evidence?limit=100'
```
