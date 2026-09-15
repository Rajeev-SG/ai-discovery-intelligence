# 01 — Ship the global observation plane from the canonical surface registry

## Outcome
Deliver the first useful product immediately: a high-fidelity observation plane rendering every entry in `config/surfaces.yaml`.

## Adopted stack
Next.js App Router + TanStack Table v9 + TanStack Virtual + Radix/shadcn primitives. Do not substitute AG Grid or build grid mechanics.

## Requirements
- Search across surface/vendor/family/region/retrieval fields.
- Sort by priority, surface, vendor, confidence/evidence freshness once present.
- Faceted filters for geography, tier, surface type, vendor and retrieval status.
- Expand rows **and evidence-bearing cells** into a detail panel/drawer containing distribution channels, discovery modes, official URLs, current unknowns and evidence placeholders.
- Persist meaningful table state in the URL.
- Dense desktop layout with responsive mobile detail view; accessibility/keyboard navigation must work.
- Explicitly render `unknown/under_documented` as information, not an empty cell.

## Real product proof required
- Render all canonical surfaces from the YAML registry.
- Show ChatGPT, DeepSeek, Doubao, Qwen, NAVER and Yandex in the same product.
- Provide screenshot or deployed/local-browser capture proving: search `China`, one filter, one sort and one expanded DeepSeek row.
- State the rendered surface count and match `scripts/validate_scaffold.py`.

## Done when
The product is already useful as a global surface map before any automated ingestion exists. An empty shell, mocked table or synthetic-only fixture does not count.
