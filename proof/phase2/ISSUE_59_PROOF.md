# Issue #59 — evidence-backed marketing implications: product proof

Generated from the **real production claim ledger** (42 validated claims across 35
registry surfaces). Raw captures stay private; every value below is copied from a
validated claim.

## What shipped

- `src/ai_discovery/implications.py` — a deterministic, auditable implication
  engine. `IMPLICATION_RULES` maps a canonical mechanics dimension + a ledger
  topic to one marketer action family. A rule fires only when the surface's
  mechanics projection carries an *evidenced* dimension of that kind **and** a real
  claim on that surface has the rule's topic. No model output, no free-form
  recommendations, no GEO/AEO filler.
- API: `GET /implications` (all surfaces + the merged cross-surface list) and
  `GET /surfaces/{id}/implications`.
- UI: `/implications` (`web/components/implications-list.tsx`) — each card shows
  the action, why it follows, the supporting claim ids, the surfaces/regions it
  applies to, and, kept distinct, its **confidence** and its **actionability**;
  evidence-free surfaces render an explicit **monitor-only** state.

## Data contract (every implication carries)

supporting claim/evidence ids · applicable surfaces, modes and regions ·
confidence · rationale · actionability (distinct from confidence) · significance
(reusing the tested `pov.significance_of` machinery) · contradicting evidence ·
and an explicit `monitor_only` flag.

## 1. Real implications from the live ledger

Live `GET /implications`: **5** merged implications across **4** surfaces, plus
**31** surfaces in the explicit monitor-only state.

| Family | Actionability | Confidence | Significance | Surfaces | Supporting claims |
|---|---|---|---|---|---|
| Eligibility & crawlability | high | low | 3.63 | chatgpt | `0b187a5b…`, `3cc01c09…`, `5b7bd7ca…` |
| Eligibility & crawlability (site-side) | high | low | 3.63 | chatgpt | (same) |
| Indexability & freshness | high | low | 3.63 | chatgpt | (same) |
| Citation visibility | medium | low | 3.61 | chatgpt, google-ai-mode, google-ai-overviews | `71357b0d…`, `32d51457…`, `220eaa9c…`, `5afa38dd…` |
| Query & topic coverage | medium | low | 3.29 | 4 surfaces | `7105fbb6…`, `3a29f02e…`, `e1048f9a…`, `d1bd43f7…`, `f3b53af1…` |

Screenshot: `web/proof/implications-desktop.png` — the eligibility implication,
its "why", its supporting claim ids, and the separate confidence / actionability
badges.

## 2. Cross-surface vs surface-specific

- The citation-visibility implication is emitted **once**, naming all three
  surfaces that share the evidenced `citation_presentation` mechanic (`chatgpt`,
  `google-ai-mode`, `google-ai-overviews`).
- A mechanic only one surface holds stays scoped to that surface.

## 3. Unknown / monitor-only is a real output

`google-gemini`, `claude` and 29 other surfaces return
`monitor_only: true` with the note *"No evidenced, marketer-actionable mechanic
for this surface yet. Monitor rather than act: unknown is a valid answer."* — no
invented advice.

## 4. Acceptance evidence

- **Every displayed implication is evidence-linked** — every card lists
  `supported_by` claim ids; a rule with no supporting claim never fires.
- **No generic GEO advice** — test `test_no_generic_geo_filler_text` asserts the
  rule text contains no GEO/AEO/ranking filler.
- **Cross-surface** — `test_cross_surface_implication_merges_shared_mechanics`;
  **surface-scoped** — `test_surface_specific_implication_stays_scoped`.
- **Confidence and actionability distinct** — separate fields, both rendered
  (`test_confidence_and_actionability_are_distinct_axes`).
- **Removing the supporting evidence removes the implication** —
  `test_removing_the_supporting_evidence_removes_the_implication` and
  `test_unknown_mechanic_yields_explicit_monitor_not_action`.
- **A live contradiction caps confidence** —
  `test_contradicting_evidence_is_carried_and_caps_confidence`.

Verification: pytest **300**, ruff clean, vitest **80**, playwright **28** live.

## 5. Review-hardening pass (impl-001 … impl-005)

- **impl-001 (supersedes treated as contradiction).** A `supersedes` relationship
  now retires the superseded claim from support instead of flagging a
  contradiction and capping confidence at `low`; scope (modes/regions) is unioned
  from supporting evidence only. Test:
  `test_supersedes_is_replacement_not_contradiction`.
- **impl-002 (merge overstated significance).** A merged cross-surface implication
  now takes the **weakest** member's significance, matching the min-policy used for
  confidence and actionability. Live: merged citation-visibility significance fell
  from 3.61 to 3.36, query-coverage from 3.29 to 3.14. Test:
  `test_merge_does_not_overstate_significance`.
- **impl-003 (dead `monitor` family).** The no-action outcome is now a structured
  `Implication` with `family="monitor"`, so the API returns one shape; the wrapper
  boolean remains a convenience. Tests assert the monitor shape.
- **impl-004 (all-monitor ledger degraded to blank).** The page renders whenever
  any surface exists, so an all-monitor-only ledger shows the monitor list, never
  the generic empty state. Verified live with `EVIDENCE_FIXTURE=all-monitor`
  (`impl-monitor-list` present, `impl-empty` absent); e2e added and wired into CI.
- **impl-005 (weak tests).** Added a real high-confidence/low-actionability fixture
  proving the axes are independent, and a word-boundary filler scan over the full
  rendered payload (including notes) rather than the static rule table only.

## 6. Honest limitations

- Rules cover the mechanics dimensions the ledger can evidence today; a dimension
  with no rule (provider selection, answer type) yields no implication rather than
  a guess.
- Production confidence is currently `low` for these mechanics, which the view
  states plainly; it does not inflate the reading to make the advice look stronger.
