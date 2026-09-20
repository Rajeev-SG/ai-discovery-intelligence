# AI Discovery Intelligence (web)

The product shell. The root route (`/`) is the intelligence-first landing —
latest material changes from the live `/events` feed, the weekly executive
brief from `/brief`, and the current POV projected from the committed canonical
artifact. The supporting routes are `/surfaces` (the searchable, sortable,
filterable 35-surface registry matrix and evidence drill-down), `/pov` (the
living POV and changelog) and `/reconciliation` (the persisted reconciliation
ledger).

Evidence is served by the read-only FastAPI evidence API (`EVIDENCE_API_URL`);
the web app fetches it server-side and never re-derives a claim, confidence or
reconciliation decision in the browser. Registry facts are rendered verbatim,
with retrieval unknowns and missing evidence stated explicitly.

## Adopted stack (per `../docs/OSS_STACK.md`)

| Job | Package | Version |
|---|---|---|
| Web app | `next` (App Router) | 16.3.5 |
| Table state / sort / filter / facet / expand | `@tanstack/react-table` | 9.2.4 |
| Virtualisation | `@tanstack/react-virtual` | 3.14.13 |
| Accessible primitives | `@radix-ui/react-dialog`, `@radix-ui/react-popover` | 1.1.23 / 1.1.18 |
| Registry parsing | `yaml` | 2.8.1 |

Table v9 uses the registered-feature API: `tableFeatures({ ... })` plus
`useTable({ features, columns, data })`. Row models (`sortedRowModel`,
`filteredRowModel`, faceted models, `expandedRowModel`) are registered as
feature slots; sizing needs `columnSizingFeature` before `column.getSize()`
exists. All of this is real published v9 API, not assumed v8 behaviour.

## Run locally

```bash
npm ci
npm run dev          # or: portless run --name ai-discovery-observation-plane
```

The registry is read from `../config/surfaces.yaml`; override with
`REGISTRY_PATH` if needed.

## Checks

```bash
npm run typecheck                  # tsc --noEmit
npm test                           # vitest: registry + URL-state invariants
npm run build                      # next build
npm run e2e                        # playwright: real-browser product proof
```

The browser suite runs against a live server. Point it at one with
`PLANE_URL`; otherwise Playwright uses its configured base:

```bash
portless run --name ai-discovery-observation-plane &
PLANE_URL="https://gh-1-observation-plane.ai-discovery-observation-plane.localhost:1355/" \
  NODE_EXTRA_CA_CERTS="$HOME/.portless/ca.pem" npm run e2e
```

Screenshots are written to `proof/`.

## Product behaviours

- Search across surface, vendor, family, region and retrieval status.
- Sortable columns (priority sorts by registry tier order, not label text).
- Faceted multi-select filters for geography, priority tier, surface type,
  vendor and retrieval status, with counts from Table's faceted unique values.
- Row expansion and evidence-cell expansion into an inline panel and a Radix
  Dialog drawer: distribution channels, discovery modes, official URLs,
  retrieval unknowns and evidence placeholders.
- Meaningful state persisted to the URL (search, sort, facets, expanded rows,
  non-default column visibility) via `history.replaceState`, so an RSC
  navigation cannot drop live table state.
- Dense desktop table with a shared grid template (header and rows cannot
  drift); responsive mobile card layout with the same detail drawer.
- Keyboard support: sortable headers, row expand toggles, evidence-cell
  buttons, focus-trapped drawer, skip link.
- `unknown` / `under_documented` renders as explicit information, never an
  empty cell.

## Column model

Citation evidence, confidence and last-verified columns carry the live claim
summary for each surface when the evidence API is configured; a surface with no
linked validated claim shows an explicit no-evidence state rather than a blank
cell.
