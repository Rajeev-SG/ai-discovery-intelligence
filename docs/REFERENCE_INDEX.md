# Reference index

This is the coding-agent starting point for third-party documentation. Prefer upstream documentation over blog tutorials. Versions should be pinned during implementation and recorded in lockfiles.

## Adopted infrastructure

| Component | Role | Upstream documentation | Licence/notes |
|---|---|---|---|
| Dagster OSS | orchestration/assets/schedules/retries | https://docs.dagster.io/ | Apache-2.0 |
| changedetection.io | source-change tripwire | https://changedetection.io/ | self-hostable; verify current licence/release before pinning |
| Scrapy | crawling/discovery | https://docs.scrapy.org/ | BSD-3-Clause |
| Trafilatura | main-text/metadata extraction | https://trafilatura.readthedocs.io/ | Apache-2.0 |
| Playwright | JS-rendering fallback + E2E | https://playwright.dev/docs/intro | Apache-2.0 |
| scrapy-playwright | Scrapy/Playwright integration | https://github.com/scrapy-plugins/scrapy-playwright | BSD-3-Clause |
| RSSHub | feed generation | https://docs.rsshub.app/ | self-hostable |
| SearXNG | supplemental metasearch discovery | https://docs.searxng.org/ | AGPL-3.0; never canonical evidence |
| PostgreSQL | canonical relational store | https://www.postgresql.org/docs/ | PostgreSQL licence |
| SQLAlchemy | ORM/query layer | https://docs.sqlalchemy.org/ | MIT |
| Alembic | migrations | https://alembic.sqlalchemy.org/ | MIT |
| Pydantic | schemas/validation | https://docs.pydantic.dev/ | MIT |
| Instructor | validated LLM extraction when needed | https://python.useinstructor.com/ | use OpenRouter-compatible structured output; do not hand-roll retry/parser plumbing |
| FastAPI | API | https://fastapi.tiangolo.com/ | MIT |
| Next.js App Router | web application | https://nextjs.org/docs/app | MIT |
| TanStack Table v9 | grid state/sort/filter/facet/expand | https://tanstack.com/table/v9 | MIT |
| TanStack Virtual | virtualisation | https://tanstack.com/virtual/latest | MIT |
| Radix UI | accessible primitives | https://www.radix-ui.com/primitives/docs/overview/introduction | MIT |
| shadcn/ui | composable component recipes | https://ui.shadcn.com/docs | copy-in components; review licences of dependencies |
| pytest | Python tests | https://docs.pytest.org/ | MIT |
| Renovate | dependency automation | https://docs.renovatebot.com/ | Mend-hosted or self-hosted |
| Coolify | Hetzner deployment/control plane | https://coolify.io/docs/ | self-hosted |
| Docker Compose | local/Oracle packaging | https://docs.docker.com/compose/ | standard deployment primitive |
| Orbstack | local Docker/Linux runtime on macOS | https://docs.orbstack.dev/ | development only |
| Oracle Cloud Infrastructure | future acquisition VPS | https://docs.oracle.com/en-us/iaas/Content/home.htm | cheap/disposable acquisition plane |
| GitHub CLI | repository/issue bootstrap | https://cli.github.com/manual/ | used by scaffold scripts |
| GitHub Actions | lightweight CI where useful | https://docs.github.com/actions | do not make product operation depend on CI minutes |
| Tailscale | private connectivity | https://tailscale.com/kb | use existing private network where needed |

## Structured extraction

Use deterministic parsing where the source is already structured. For prose reports where claims/methodology cannot be reliably parsed, use Instructor + Pydantic schemas over the configured OpenRouter endpoint. LLM output is never evidence: it must point back to exact source material and pass deterministic validation. Paid inference is allowed; **paid data sources are not**.

## Platform documentation

The authoritative product/surface list is `config/surfaces.yaml`. Every entry contains official URLs. The implementation should periodically verify those URLs and add release-note/help/documentation URLs discovered from the vendor's official domain.

## Evidence-source documentation

The authoritative free source catalogue is `config/sources.yaml`. It deliberately mixes primary product evidence, free market telemetry, commercial-vendor research, editorial discovery and open research infrastructure. `docs/SOURCE_STRATEGY.md` defines how those classes may be used.

## Rule for agents

Do not add a generic dependency merely because it is popular. Do not replace an adopted component merely because another tool looks newer. First prove an unmet requirement under `docs/BUILD_VS_ADOPT_POLICY.md`.
