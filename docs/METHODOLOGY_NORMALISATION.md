# Methodology and metric normalisation

Different studies often use similar words for different denominators. Never merge them merely because the headline numbers look comparable.

## Required study metadata

Capture, where available:
- publisher and commercial interest;
- publication date and measured time window;
- consumer surface and exact mode;
- geography/language/device;
- prompt/query universe and how prompts were selected;
- sample size and repeat count;
- whether results came from consumer UI, API, browser automation, clickstream/panel or server logs;
- metric numerator and denominator;
- domain-level vs URL-level measurement;
- branded/non-branded and category mix;
- stochastic repetition/sampling method;
- known exclusions/limitations.

## Comparable only when definitions align

Examples that must stay distinct:
- Similarweb share of measured AI-chatbot web traffic vs Statcounter AI-chatbot market-share instrumentation;
- citation share among all citations vs mention share among top domains;
- percentage of prompts citing a domain vs percentage of citation URLs belonging to a domain;
- web visits vs app MAU vs active users within a parent ecosystem;
- AI referral sessions vs crawler requests;
- consumer-UI citations vs API-grounding sources.

## Conflict states

Use:
- `compatible_support` — materially same metric/context;
- `directional_support` — different metric but same directional implication;
- `methodologically_incomparable` — numbers should not be reconciled directly;
- `temporal_update` — newer period plausibly supersedes older period;
- `material_conflict` — sufficiently comparable studies disagree;
- `possible_transient_change` — short-lived change not yet corroborated;
- `unresolved` — insufficient evidence.

## Agency interpretation

The agency interpretation is a separate object from the source claim. It may say, for example: “Evidence indicates a short-lived or measurement-specific Reddit citation disruption; current datasets do not support the stronger claim that ChatGPT stopped using Reddit.”

Never alter source claims to make the agency narrative cleaner.
