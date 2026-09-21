# Changelog

This file records repository/product changes. The generated intelligence changelog will live separately in the canonical data store and `pov/CHANGELOG.md` once implemented.

## 2026-09-20 (issue #61)

- **Marketer-first information architecture.** The homepage now answers the four
  marketer questions in order — what platforms exist → how discovery works → how
  we know / can we trust it → why it matters — with live, evidence-derived counts
  and links into `/landscape`, `/surfaces` (Evidence & trust) and `/implications`.
  Latest changes, weekly brief and POV are demoted to a "Returning users" area.
  Navigation is reset around user-facing concepts; POV becomes "What this means"
  and Reconciliation "Evidence reconciliation" as secondary links. Proof:
  `proof/phase2/ISSUE_61_PROOF.md`.

## 2026-09-20 (issue #60)

- **Marketer-first landscape + mechanics comparison.**
  `src/ai_discovery/landscape.py` projects a curated major-surface landscape
  (name/vendor/type/priority/geography, one evidenced reach figure, discovery
  modes, mechanics coverage, one-line relevance) and a per-dimension comparison
  across the canonical mechanics onto the #56 projection. `/landscape` and
  `/landscape/comparison`; new `/landscape` UI page (grid + comparison matrix,
  comparison selection stored in the URL). Registry facts are labelled as registry
  metadata; unknown cells stay explicit. Proof: `proof/phase2/ISSUE_60_PROOF.md`.

## 2026-09-20 (issue #59)

- **Evidence-backed marketing implications.** `src/ai_discovery/implications.py`
  maps evidenced mechanics dimensions + ledger topics to marketer action families
  via an auditable rule table; every implication carries supporting claim ids,
  surfaces/modes/regions, confidence, actionability, significance (reusing the POV
  machinery) and contradicting evidence. `/implications` and
  `/surfaces/{id}/implications`; new `/implications` UI page. Unknown / no-action
  is an explicit monitor-only state. Proof: `proof/phase2/ISSUE_59_PROOF.md`.

## 2026-09-20 (issue #58)

- **Surface-alias read-path fix.** `/surface-evidence` and
  `/surfaces/{id}/evidence` (and the `?surface=` claim filter) resolve a claim's
  surface value to the canonical registry id at read time — the same resolution
  the mechanics projection uses — so a surface whose claims were stored under an
  alias (`deepseek`, `naver-ai-tab`, `kanana-in-kakaotalk`) shows its real
  evidence instead of a false "No evidence". Stored claims are never rewritten.
- **Marketer-facing evidence & trust layer.** Every evidenced mechanic now
  carries `confidence_rationale` (a one-line "why this confidence"), freshness,
  publisher, public URL, evidence class, dates and methodology; the mechanics
  endpoints join the single reconciliation service onto each evidence entry so
  conflicts render inline. New UI (`web/components/mechanics-trust.tsx`) renders
  the three simple evidence classes with the technical record behind progressive
  disclosure, wired into the surface detail drawer under "Evidence & trust".
- **Explainable confidence for the LLM lane.** The `llm_proposal` extraction lane
  no longer hardcodes `medium`; it derives confidence from evidence like the
  deterministic lane (repo rule 11 / issue #28A), so every persisted claim can
  explain its label.
- Proven on the real production ledger; see `proof/phase2/ISSUE_58_PROOF.md`.
- Review-hardening (frontier F1–F5): freshness is derived at serialization time
  from `observed_at` (never frozen by the projection cache); the reconciliation
  index is cached on the ledger token and the read path is confirmed pure; added a
  real-Postgres test for the alias-aware `jsonb ?|` filter; the read path derives
  the why-confidence for claims persisted without a stored rationale; and the
  freshness thresholds have one shared implementation.

## 2026-09-19 (issue #7)

- Living POV shipped as product data: `pov/state.yaml` (stable proposition ids,
  owner topics, evidence bullets, append-only changelog), `config/pov_policy.yaml`
  (deterministic editorial gate), and `scripts/build_pov.py` (regenerates
  `docs/EXECUTIVE_POV.md` and `pov/CHANGELOG.md` from the ledger).
- Proven on the live ledger: one real evidence change (a `crawler_index_policy`
  claim) updated exactly one proposition with a before/after changelog entry, and
  the generator is idempotent on re-run. A current event outside a proposition's
  topics, an implication, and a low-confidence claim each correctly produce no POV
  change. Evidence in `proof/live/ISSUE_7_LIVING_POV_PROOF.md`.
- CI: a deterministic POV-gate smoke check runs on every push; `pov/**` and
  `config/**` are now CI trigger paths.

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
