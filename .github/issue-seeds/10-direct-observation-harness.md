# 10 — Later: add controlled consumer-surface observation only where lawful, stable and worth it

## Status
Post-v1 enhancement; do not block issues 01–09.

## Outcome
Measure behaviour that public documentation/research cannot answer, while keeping observed behaviour distinct from vendor-documented facts.

## Constraints
- Review terms, authentication and automation constraints per surface before probing.
- Prefer deterministic Playwright automation over an LLM browser agent for repeatable tests.
- Preserve surface, model/mode where visible, locale, account state, prompt, timestamp, query fan-out/citations when observable and raw response hash.
- Repeat enough samples to avoid presenting stochastic snapshots as stable facts.
- Never claim API behaviour equals consumer-UI behaviour.

## Product proof required
Start with one permitted, reproducible surface and one commercially meaningful question. Run repeated observations, render distribution/variance and link the observed result to the existing evidence ledger. No synthetic-only benchmark qualifies.
