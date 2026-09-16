# AI Discovery Intelligence

A continuously maintained, source-backed view of how major consumer AI discovery surfaces find, retrieve, cite and recommend information — and what commercially significant changes mean for brands.

This repository is designed for coding-agent-first development. A single agent should be able to clone it, read `AGENTS.md`, inspect the ordered GitHub issues, and work autonomously through the roadmap. Every implementation issue must end in a useful product output that a media/SEO leader can inspect — never merely “the pipeline runs”.

## v1 principles

- **Free data sources only.** No paid Peec, Similarweb, Semrush, Ahrefs, Profound, SISTRIX or other data subscriptions are required for v1. Their freely accessible research/blog output may be ingested.
- **Global consumer coverage.** Track globally important and regionally dominant AI chat/search interfaces, including China, Russia/CIS and Korea — not just ChatGPT/Gemini/Claude.
- **Evidence before opinion.** Keep source, date, geography, methodology, sample size and provenance for every claim.
- **Conflict is data.** Contradictory studies are preserved and reconciled; the system must not collapse them into false certainty.
- **Senior-leader restraint.** The weekly brief and POV contain only material developments that change media/search/discovery strategy.
- **Adopt before build.** Mature, stable OSS/self-hosted software must be preferred for generic infrastructure. Custom code is reserved for domain semantics and product-specific logic.
- **Product proof for every stage.** Every issue requires a visible real-world output, example claim, report, table, brief, or deployed behaviour.

## Start here

1. Read [`AGENTS.md`](AGENTS.md).
2. Read [`docs/AGENT_BOOTSTRAP.md`](docs/AGENT_BOOTSTRAP.md).
3. Read [`docs/V1.md`](docs/V1.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
4. Work the numbered GitHub issues in order unless an issue explicitly says otherwise.
5. Read [`docs/ISSUE_MAP.md`](docs/ISSUE_MAP.md) for the staged product roadmap.
6. Never close an issue without the required product proof.

## Product surfaces

The primary product is a searchable, sortable, filterable observation plane showing each consumer AI surface, its retrieval/search behaviour, citations, crawl/index controls, commercial surfaces, latest material changes, confidence and evidence. Cells stay concise; expansion reveals evidence history and conflicting observations.

The secondary product is a deliberately short executive weekly brief and a versioned agency SEO/AEO/GEO POV with a full changelog.

## Deployment intent

- **Development:** local Docker/Orbstack.
- **Acquisition plane:** Oracle VPS when available; cheap/disposable fetch, change-detection and browser work.
- **Durable app/data plane:** existing Hetzner VPS, managed with Coolify.
- **Private connectivity:** Tailscale where useful.

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Product surfaces (implemented)

- **Observation plane** — `web/`, a Next.js App Router app rendering every
  entry in `config/surfaces.yaml` with search, sort, faceted filters,
  expandable rows/evidence cells, URL state and a responsive mobile view.
  Run it with `cd web && npm ci && npm run dev` (or
  `portless run --name ai-discovery-observation-plane`). See
  [`web/README.md`](web/README.md) for the proof and the check commands.

## Repository bootstrap

See [`docs/REPOSITORY_SETUP.md`](docs/REPOSITORY_SETUP.md). The scaffold includes an idempotent GitHub issue bootstrap script.
