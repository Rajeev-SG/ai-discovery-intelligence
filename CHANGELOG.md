# Changelog

This file records repository/product changes. The generated intelligence changelog will live separately in the canonical data store and `pov/CHANGELOG.md` once implemented.

## 2026-09-16

- Shipped issue 01, the global observation plane (`web/`) from the canonical
  surface registry: all 35 surfaces rendered with search over surface/vendor/
  family/region/retrieval, sortable columns, faceted filters (geography,
  priority tier, surface type, vendor, retrieval status), row and evidence-cell
  expansion, URL state persistence, keyboard navigation and a responsive mobile
  view. Built on the adopted stack — Next.js App Router, TanStack Table v9,
  TanStack Virtual and Radix primitives.
- The plane shows registry facts only. Retrieval unknowns and missing evidence
  are rendered as explicit information, not empty cells and not invented
  research; live provenance remains issues 02/03.
- Added `web/` unit tests, a real-browser Playwright proof suite with committed
  screenshots in `web/proof/`, and a GitHub-hosted `web-ci` workflow.

## 2026-09-15

- Initial agent-first scaffold.
- Defined free-source-only v1.
- Added global consumer-surface scope, including major Chinese and regional discovery interfaces.
- Selected an OSS-first stack and explicit build-vs-adopt policy.
- Added ordered implementation issue seeds requiring useful product proof.
