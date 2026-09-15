# 09 — Deploy the proven product using local Orbstack → Oracle acquisition → Hetzner/Coolify durable architecture

## Outcome
Move the useful product to durable self-hosted production without inventing infrastructure.

## Target split
- Local Orbstack/Docker Compose remains the development baseline.
- Oracle VPS: disposable/cheap acquisition plane — changedetection.io, Scrapy workers, Playwright Chromium, RSSHub, optional SearXNG and temporary evidence cache.
- Hetzner/Coolify: PostgreSQL, Dagster, API, web app, durable metadata/backups.
- Tailscale: private machine-to-machine connectivity where appropriate.
- No unique durable state may exist only on Oracle.

## Requirements
- Compose/Coolify deployment manifests with pinned versions and health checks.
- Backup/restore documented and exercised for PostgreSQL.
- Secrets never committed.
- Source acquisition can fail/restart without corrupting canonical evidence.
- Observability uses component-native health/status first; do not build a custom infra dashboard.

## Real product proof required
Provide a production URL or internally reachable deployment, show live observation-plane data, trigger one source refresh end-to-end, and document the evidence record/change produced. Include backup/restore proof.
