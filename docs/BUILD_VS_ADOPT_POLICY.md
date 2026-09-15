# Build vs adopt policy

The default answer for generic infrastructure is **adopt**.

## Agent decision rule

Before adding a generic subsystem, ask:

1. Is this domain-specific to AI discovery intelligence?
2. Does the adopted stack already provide it?
3. Is there a mature OSS/self-hosted tool that clearly provides it?
4. Would custom code meaningfully improve the product, rather than merely duplicate plumbing?

If answers are `no / yes / yes / no`, do not build it.

## Always adopt where available

Scheduling, crawling, retries, change detection, RSS bridging, browser rendering, migrations, DB pooling, API serving, data-grid mechanics, virtualisation, accessible dialogs/dropdowns, logging and dependency updates.

## Appropriate custom code

- platform/surface taxonomy;
- source registry configuration;
- claim/evidence schema mapping;
- methodology normalization;
- conflicting-evidence reconciliation;
- confidence scoring rules;
- commercial-significance scoring;
- executive editorial policy;
- POV update logic;
- domain-specific UI summaries.

## ADR trigger

An ADR is mandatory if an agent proposes:

- a new service not listed in `OSS_STACK.md`;
- replacing an adopted component;
- >150 lines of generic infrastructure code;
- a paid dependency/data source in v1;
- a new state store, queue, search engine or scheduler.

The ADR must name the exact unmet requirement, chosen option, at least two mature alternatives, operational cost and rollback path.
