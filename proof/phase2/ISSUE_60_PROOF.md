# Issue #60 — marketer-first landscape + mechanics comparison: product proof

Generated from the **real production claim ledger** (42 validated claims across 35
registry surfaces) plus the canonical registry. Registry facts are copied verbatim
and labelled as registry metadata; every reach figure, coverage count and
comparison cell comes from a validated claim or is an explicit unknown.

## What shipped

- `src/ai_discovery/landscape.py`: a **curated** marketer-facing landscape over the
  registry (ChatGPT, Gemini, Google AI Mode, Claude, Perplexity, DeepSeek, Doubao),
  each with name/vendor, product type, priority/geography, one evidenced reach
  figure, discovery modes, mechanics coverage/confidence, and a one-line relevance
  grounded in evidenced mechanics.
- A mechanics comparison across the canonical dimensions
  (`COMPARISON_DIMENSIONS`, a marketer-readable subset of the 13) built directly
  from the #56 projection: each cell is the surface's state with its lead claim, an
  evidence class and a confidence; a cell with no evidence is an explicit
  `unknown`.
- API: `GET /landscape` and `GET /landscape/comparison?surfaces=a,b,c`.
- UI: `/landscape` — the primary landscape grid plus the comparison matrix, with
  the comparison selection stored in the URL so it is shareable. The exhaustive
  35-surface registry remains at `/surfaces`.

## 1. Real landscape (live ledger)

| Surface | Vendor | Coverage | Evidenced reach |
|---|---|---|---|
| ChatGPT | OpenAI | 7/13 | market share: 79.4 percent |
| Gemini | Google | 0/13 | market share: 10.9 percent |
| Google Search AI Mode | Google | 4/13 | monthly users: 1,000,000,000 |
| Claude | Anthropic | 0/13 | market share: 2.57 percent |
| Perplexity | Perplexity | 3/13 | market share: 4.31 percent |
| DeepSeek Chat | DeepSeek | 0/13 | market share: 0.02 percent |
| Doubao / 豆包 | ByteDance | 0/13 | avg monthly usage time: 144.6 minutes |

Screenshot: `web/proof/landscape-desktop.png`.

## 2. Comparison (live ledger)

Screenshot: `web/proof/landscape-comparison.png` — 6 surfaces × 9 dimensions, e.g.
`retrieval_provider`: ChatGPT **Known** (Ahrefs, independently researched),
Google AI Mode **Known** (vendor-documented), Perplexity **Known**
(vendor-documented), Gemini/Claude/DeepSeek **Unknown (explicit)**.

## 3. Acceptance evidence

- **"What are the main AI chat/search products?"** — answered by the primary
  landscape (7 curated surfaces incl. a regional/China surface, Doubao).
- **Compare discovery mechanics across surfaces** — the comparison matrix.
- **Market share is contextual** — one reach figure per card, with its claim id;
  never the organising layer.
- **Evidence/unknown/conflict visible per dimension** — each cell shows state,
  evidence class, confidence and an evidence link, or an explicit unknown.
- **35-surface registry preserved** — `/surfaces` unchanged, linked from the page.
- **Desktop/mobile + accessibility** — responsive grid; the comparison is a real
  `<table>` with `scope` row/column headers; e2e runs on both viewports.

Tests: `test_landscape.py` (curated ids only, coverage from evidence, reach is the
surface's own metric not a joint claim's, unknown kept explicit, cell carries its
evidence link). Verification: pytest **311**, ruff clean, vitest **84**, playwright
**33** live.

## 4. Product proof (issue #60)

The comparison includes **ChatGPT, Gemini/AI Mode, Claude, Perplexity, DeepSeek**
and the regional/China surface **Doubao** in the landscape (6 in the default
comparison set).

## 5. Honest limitations

- The landscape is a **curated** view; the registry status is still coarse and is
  labelled as registry metadata, never as mechanics evidence.
- Reach figures are whatever single usage claim the ledger holds; a surface with
  no usage claim shows no figure rather than an estimate.
