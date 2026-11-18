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

The public surface `<https://rajeevg.com/solutions/ai-discovery>` is a Vercel
project, `ai-discovery-observation-plane` (team `rajeevgills-projects`). It is
git-connected to this repository with root directory `web`, so a push to `main`
that touches `web/**` deploys production automatically and rajeevg.com proxies
the result. Data refreshes stay independent of frontend deployments: content
changes land in `web/content/surfaces/*.yaml` and every such merge is a deploy.
See [`OPERATIONS.md`](OPERATIONS.md#production-web-deploy) for verification,
rollback and the manual fallback.
