# OSS adoption guide

## Default decision

If a requirement is generic infrastructure, assume a mature OSS component already exists. Search upstream docs, releases and issue trackers before writing code.

## Generic jobs that must not be rebuilt

- scheduling, retries, lineage or job UI;
- crawling, robots handling, concurrency/backoff;
- HTML/main-text extraction;
- browser automation/rendering;
- page-diff/change detection;
- RSS/feed bridging;
- SQL persistence/migrations;
- full-text search;
- table sorting/filtering/faceting/expansion/virtualisation;
- accessible dialogs/tooltips/dropdowns;
- structured LLM validation/retry plumbing;
- deployment dashboards;
- dependency-update automation.

## What bespoke code is for

- AI-discovery surface taxonomy;
- source registry and evidence semantics;
- claim normalisation;
- methodology capture;
- support/contradiction/supersession relationships;
- confidence and commercial-significance logic;
- POV/editorial rules;
- domain-specific table columns and drill-downs.

## Mandatory ADR trigger

Create an ADR before any of the following:

- adding a new stateful infrastructure service;
- replacing an adopted v1 component;
- building more than ~150 lines of generic infrastructure logic;
- introducing a paid data source/API into v1;
- adding a queue, vector database, search cluster or second orchestrator;
- building custom grid/crawler/change-detection/feed infrastructure.

The ADR must state the unmet requirement, at least two existing alternatives checked, maturity/maintenance/licence/deployment fit, operational cost, why the adopted stack cannot meet it, and rollback path.
