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

## 5. Review-hardening pass (frontier findings)

- **URL-state desync.** The comparison selection is re-derived from `?compare=`
  when the URL changes underneath the view (back/forward, a pasted link), so a
  shared selection is honoured rather than overwritten by stale local state. e2e:
  *a shared `?compare=` URL round-trips and survives back/forward*.
- **Duplicate surface ids.** `GET /landscape/comparison` dedupes before validating
  the 2–6 range, so `?surfaces=chatgpt,chatgpt` returns 400 (one distinct surface),
  not a two-surface claim. Test:
  `test_comparison_endpoint_rejects_duplicate_surface_ids`.
- **Dead comparison endpoint / divergent validation.** Unknown ids in a shared URL
  are now surfaced explicitly (`compare-dropped`) rather than silently filtered, so
  the client and the validated `/landscape/comparison` endpoint do not diverge
  silently; e2e covers it.
- **Reach name-matching heuristic.** Reach association is now token-based with the
  vendor name excluded, so a joint "Google AI users" claim is attributed to
  *neither* Gemini nor AI Mode, and a joint claim naming neither surface yields no
  figure. Tests: `test_reach_is_none_when_a_joint_claim_names_neither_surface`,
  `test_vendor_ambiguous_joint_claim_is_not_attributed`.

## 6. Honest limitations

- The landscape is a **curated** view; the registry status is still coarse and is
  labelled as registry metadata, never as mechanics evidence.
- Reach figures are whatever single usage claim the ledger holds; a surface with
  no usage claim shows no figure rather than an estimate.
