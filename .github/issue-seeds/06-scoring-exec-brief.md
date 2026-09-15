# 06 — Add evidence confidence, commercial significance and the restrained weekly executive brief

## Outcome
Produce the thing senior media leaders actually need: only material changes, with clear confidence and action.

## Policy
Implement `config/significance.yaml` and `config/executive_policy.yaml`. Evidence confidence and commercial significance are separate axes. Do not substitute LLM “confidence”.

## Requirements
- Score reach, commercial intent, magnitude, breadth, persistence and actionability.
- Score evidence authority/directness, methodology, sample strength, recency, geography fit and corroboration; penalise unresolved material conflict.
- Generate 0–3 items by default, hard maximum 5.
- Each item: Change; Why it matters; Agency action/monitor-only; Confidence; evidence IDs.
- Exclude model benchmarks, developer-only releases, minor UI tweaks, generic GEO tips and repeated non-incremental coverage unless they alter consumer discovery strategy.
- Keep technical detail in drill-down, not executive copy.

## Real product proof required
Generate a weekly brief from the live corpus. Demonstrate at least one high-noise candidate that is correctly excluded and one material change that is included. The Reddit conflict must not be reported as an unqualified fact.
