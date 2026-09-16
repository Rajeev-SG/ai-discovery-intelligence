# Proof — issue 01 observation plane

## What was delivered

A working observation plane at `web/` that renders **every** entry in
`config/surfaces.yaml`, with search, sort, faceted filters, row/evidence
expansion, URL state, keyboard navigation and a responsive mobile view.

Built on the adopted stack from `docs/OSS_STACK.md`: Next.js App Router
16.3.5, TanStack Table **9.2.4**, TanStack Virtual 3.14.13 and Radix
primitives. No grid mechanics were built by hand, and no AG Grid / Tabulator
fallback was introduced.

## Rendered surface count

- `scripts/validate_scaffold.py` → `OK: 35 surfaces; scaffold invariants valid`
- The plane renders **35** surfaces (asserted in the browser as
  `data-testid="registry-count"` = 35 and `surface-count` = 35 at rest).
- Unit test asserts `toSurfaceRows(loadRegistry()).length === 35`.

The count is not a mock: rows are projected from the YAML registry at request
time and the page reads it from disk (`loadRegistry()`), with
`REGISTRY_PATH` available as an override.

## Required real product proof

Requirement: *show ChatGPT, DeepSeek, Doubao, Qwen, NAVER and Yandex in the
same product; prove search `China`, one filter, one sort and one expanded
DeepSeek row.*

All six surfaces are in one product and asserted in `web/e2e`:

| Surface | Registry id | Proof |
|---|---|---|
| ChatGPT | `chatgpt` | `desktop-registry.png` |
| DeepSeek | `deepseek-chat` | `desktop-expanded-deepseek.png` |
| Doubao | `doubao` | `desktop-search-china.png` |
| Qwen | `qwen-consumer` | `desktop-search-china.png` |
| NAVER | `naver-ai` | `/search?q=NAVER` assertion |
| Yandex | `yandex-ai-search` | `/search?q=Yandex` assertion |

The browser suite also scrolls the virtualized body and asserts that all 35
row ids render, so "every canonical surface" is verified rather than assumed.

### Evidence: search `China`

`web/proof/desktop-search-china.png` — 10 of 35 surfaces match, ordered by
priority: DeepSeek Chat, Doubao, Qwen, Quark AI, Yuanbao, … ChatGPT is
correctly excluded. `result-summary` reads
`10 of 35 surfaces matching “China” · sorted by priority asc`.

### Evidence: one filter

`web/proof/desktop-filter-tier.png` — priority tier `Core — global` applied
with the `China` search still active. The facet is populated from Table's
faceted unique values, so the count reflects the other active constraints.

### Evidence: one sort

`web/proof/desktop-sort.png` — Surface column sorted descending;
`result-summary` reads `sorted by name desc`, and the first row genuinely
changes between the ascending and descending clicks.

### Evidence: expanded DeepSeek row

`web/proof/desktop-expanded-deepseek.png` — the expanded row shows
DeepSeek's registry facts (Global, China · Web, Mobile · Web Search,
Answers), four explicit retrieval unknowns, and both official URLs
(`chat.deepseek.com`, `api-docs.deepseek.com`). The evidence section states
`Not yet ingested`.

### Evidence: mobile + keyboard

- `web/proof/mobile-registry.png` — mobile card layout, full registry.
- `web/proof/mobile-detail-deepseek.png` — mobile detail drawer with
  retrieval unknowns and official URLs.
- `web/proof/desktop-keyboard.png` — keyboard-only flow: type in search,
  Enter on a sortable header, Enter to expand, Enter on an evidence cell to
  open the focus-trapped drawer, Escape to close.

## Unknowns are information, not empty cells

`retrieval_status` drives explicit content. `under_documented` and
`heterogeneous` produce four stated unknowns; `partially_documented` produces
three; `documented_in_part` produces two. 17 of 35 surfaces are flagged
`Unknown —` in the retrieval column and 24 are priority-core.

Nothing about evidence is invented: citation evidence reads `Not yet
ingested`, confidence reads `Not yet assessed`, and last-verified reads
`Registry reviewed 2026-09-15`. A unit test asserts those placeholder values
and asserts the registry rows carry no fabricated metrics. Live provenance is
issues 02/03 and conflict reconciliation is issue 04; the drawer links each
placeholder to the issue that owns it.

## Commands run

```bash
python3 scripts/validate_scaffold.py     # OK: 35 surfaces
cd web && npm run typecheck              # tsc --noEmit, clean
cd web && npm test                       # 11 unit tests pass
cd web && npm run build                  # next build, success
cd web && npm run e2e                    # 6 passed, 4 skipped (viewport-scoped)
```

Local URL via portless:
`https://gh-1-observation-plane.ai-discovery-observation-plane.localhost:1355`

## Known limitations

- No evidence ingestion (deliberately out of scope for issue 01).
- `tier` priority ordering is a presentation rank derived from the registry's
  own `tier` field; it is not new evidence.
- Facet counts reflect the current filtered row set, which is Table's faceted
  behaviour rather than a global census.
- 17 surfaces have genuinely undocumented retrieval; the plane states this
  rather than implying coverage that does not exist.
