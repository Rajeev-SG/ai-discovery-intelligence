# Changelog

This file records repository/product changes. The generated intelligence changelog will live separately in the canonical data store and `pov/CHANGELOG.md` once implemented.

## 2026-09-19

- Issue #9 live operational proof: the PR #42 Oracle acquisition worker kit is
  deployed and running unattended (systemd timer + restricted-key DB tunnel +
  snapshot replication). A real production refresh completed end to end
  (acquisition -> snapshot -> Instructor extraction -> validated claim ->
  change event -> evidence API -> live observation plane) with the durable
  Hetzner ledger showing 51 sources, 12 evidence items, 1 claim, 1 change event.
  Oracle's private snapshot store is byte-identical on Hetzner after each run
  (35 files, matching manifest hash), so no unique durable state is Oracle-only.
  Evidence attached in `proof/live/ISSUE_9_LIVE_PROOF.md`.
- Fixed two defects the live run exposed: the automated extraction lane now
  marks quote-verified claims `human_reviewed=True` (otherwise the ledger
  provenance guard rejected every `llm_proposal` claim and production persisted
  zero claims), and change events are now derived from validated claims
  deterministically (`change_derivation.py`) so `/events` is populated.
- Fixed two Oracle worker-kit deployment bugs: connect to Hetzner over its
  public IP (Tailscale SSH intercepts `:22` on the tailnet address and requires
  interactive auth, which an unattended systemd tunnel can never satisfy) and
  address the rrsync target relative to its root.

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
