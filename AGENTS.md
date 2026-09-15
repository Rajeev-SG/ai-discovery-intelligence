# Coding agent policy

This repository is intentionally optimized for autonomous coding agents.

## Non-negotiable operating rules

1. Read this file, `docs/AGENT_BOOTSTRAP.md`, `docs/V1.md`, `docs/ARCHITECTURE.md`, `docs/OSS_STACK.md`, `docs/OSS_ADOPTION_GUIDE.md`, `docs/REFERENCE_INDEX.md`, `docs/ACCEPTANCE_STANDARD.md`, `docs/RETRIEVAL_TAXONOMY.md`, `docs/METHODOLOGY_NORMALISATION.md`, and the current issue before changing code.
2. Work open implementation issues in numeric order unless dependencies require otherwise.
3. **Do not invent infrastructure.** Before writing generic infrastructure, check the adopted OSS stack and `docs/BUILD_VS_ADOPT_POLICY.md`.
4. If mature adopted OSS already provides scheduling, crawling, change detection, article extraction, browser rendering, data-grid behaviour, migrations, orchestration, retries, lineage or observability, use it.
5. Custom code should primarily cover domain semantics: source configuration, evidence normalization, claim extraction, confidence/significance logic, POV synthesis and product-specific presentation.
6. A new generic subsystem or >150 lines of infrastructure-style custom code requires an ADR documenting why the adopted solution is insufficient and at least two mature alternatives considered.
7. Do not replace a selected OSS component because another option is fashionable. Change architecture only when evidence shows a concrete unmet requirement.
8. Do not use paid data APIs or paid visibility datasets in v1. Free public research/blogs, public APIs, RSS, sitemaps and official docs are allowed.
9. Preserve source provenance and methodology. Never present a vendor study as an objective universal truth.
10. Never hide contradictory evidence. Store it, display it, and let the confidence/reconciliation layer explain it.
11. Never use LLM self-confidence as evidence confidence.
12. The executive output must stay short. Technical detail belongs in evidence drill-down, not the weekly brief.

## Definition of done for every implementation issue

An issue is not done because code compiled or a service started. It is done only when all of the following are true:

- acceptance criteria are met;
- tests/validation pass;
- relevant docs/config are updated;
- a real useful product output is produced from real source data;
- the issue/PR contains the exact example, screenshot, URL or generated artifact proving that output;
- no bespoke generic subsystem was introduced without an approved ADR;
- the agent states known limitations and any unresolved source coverage gaps.

## Source hierarchy

Prefer, in order:

1. official product/search/crawler docs and release notes;
2. official telemetry/research from analytics/search providers;
3. large-sample specialist research with published methodology;
4. reputable specialist journalism;
5. community observations as discovery signals only.

## Safety and collection behaviour

Respect robots directives, publisher terms, rate limits and access controls. Do not bypass authentication, CAPTCHAs, bot protection or paywalls. Prefer RSS, sitemaps and documented endpoints to browser automation. JS rendering is a fallback, not the default.
