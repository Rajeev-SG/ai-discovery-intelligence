# Deployment

## Development

Run infrastructure locally in Orbstack/Docker Compose on the primary Mac. Keep production-equivalent service boundaries, but do not duplicate services merely for development convenience.

## Production split

### Oracle VPS — acquisition plane

When available, use Oracle for cheap/disposable acquisition work:

- changedetection.io;
- Scrapy fetch workers;
- Playwright/Chromium fallback jobs;
- RSSHub;
- optional SearXNG supplemental discovery;
- temporary evidence cache.

No unique durable state should exist only on Oracle.

### Hetzner + Coolify — durable plane

Use the existing Hetzner VPS/Coolify for:

- PostgreSQL canonical data;
- Dagster services/metadata;
- FastAPI service;
- Next.js observation/product UI;
- durable evidence metadata and backups;
- internal routing/auth where needed.

### Connectivity

Prefer Tailscale/private networking for Oracle-to-Hetzner service traffic. Expose only the product endpoints that need public access.

## Vercel

Vercel is not required for v1. If a later public `rajeevg.com/solutions` surface is desired, keep data refreshes independent of frontend deployments.
