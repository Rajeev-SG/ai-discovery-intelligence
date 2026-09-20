# Issue #58 — marketer-facing evidence & trust layer: product proof

Generated from the **real production claim ledger** (42 validated claims across
35 registry surfaces; source classes official / visibility_research /
market_telemetry / editorial_discovery). Raw captures stay private; every value
below is copied from a validated claim.

## What shipped

- **Surface-alias read-path fix (the #58 blocker).** The legacy
  `/surface-evidence` and `/surfaces/{id}/evidence` paths grouped claims by the
  *raw* surface value, so a surface whose claims were stored under an alias
  (`deepseek`, `naver-ai-tab`, `kanana-in-kakaotalk`) rendered "No evidence"
  while its mechanics projection showed evidence. Both paths now resolve the
  alias to the canonical registry id at **read time** (claims are never
  rewritten), reusing the same `resolve_surface_id` as the mechanics path:
  `registry.surface_id_variants` + `observations.surface_evidence` +
  alias-aware `claims.load_expanded_claims` SQL filter.
- **Trust contract on every evidenced mechanic.** Each evidence entry now carries
  `confidence_rationale` (a one-line "why this confidence"), `freshness_state`
  and `freshness_age_days`, in addition to publisher, public URL, evidence class,
  dates, methodology notes/limitations and scope.
- **Inline reconciliation, not reimplemented.** The mechanics endpoints join the
  one reconciliation service (`reconciliation_index` → `reconcile_persisted`)
  onto each evidence entry, so a conflict renders inline and links to the full
  comparison. Nothing is re-derived in React.
- **Explainable confidence for the LLM lane.** The `llm_proposal` extraction lane
  previously hardcoded `confidence="medium"` with empty inputs/rationale (repo
  rule 11 / issue #28A). It now runs the same evidence-derived assessment as the
  deterministic lane, so every persisted claim can explain its confidence.
- **Marketer UI.** `web/components/mechanics-trust.tsx` renders the backend
  projection with the three simple evidence classes (Vendor-documented /
  Independently researched / Directly observed), a one-line "why this
  confidence", freshness, methodology, limitations, scope, and inline conflicts —
  with the technical record collapsed behind progressive disclosure. It is wired
  into the surface detail drawer under "Evidence & trust".

## 1. The alias gap, fixed (real production data)

Before: `GET /surfaces/deepseek-chat/evidence` → `no_evidence` ("No validated
claim is linked to this surface yet.") while `/surfaces/deepseek-chat/mechanics`
held claims stored under `deepseek`.

After (this branch, against the real ledger):

```
GET /surfaces/deepseek-chat/evidence   -> evidence_state: evidenced, 3 claims
GET /claims?surface=deepseek-chat      -> total: 3
GET /surface-evidence  (bulk keys)     -> deepseek-chat, kakao-kanana, naver-ai
                                          (canonical ids, not raw aliases)
```

Screenshot: `web/proof/evidence-trust-deepseek.png` — DeepSeek shows
"3 validated claims" (previously "No evidence"), while its mechanics honestly
shows "0 of 13 dimensions evidenced".

## 2. Confidence, freshness and "why this confidence" (real evidence)

Full ChatGPT mechanics payload from the live ledger shows the median case:

- `search_trigger` — Independently researched (Ahrefs), low confidence,
  freshness **fresh · 3d**, WHY: `source class visibility_research`.
- `crawling_indexing_controls` — Vendor-documented (OpenAI), medium confidence,
  freshness fresh, claim `0b187a5b...` ("It can take approximately 24 hours for
  OpenAI's systems to adjust for search results after a site's robots.txt
  update.").
- `citation_presentation` — Independently researched, medium confidence, with
  **28 inline reconciliation records** joined onto the claim.

Screenshot: `web/proof/evidence-trust-chatgpt.png` — publisher, evidence class,
public URL, dates, why-confidence, methodology and limitations all visible in one
place; the technical record is collapsed.

## 3. The four required trust cases

| Case | Where proven |
|---|---|
| High-confidence official claim | ChatGPT `crawling_indexing_controls` (OpenAI docs) — live ledger |
| Medium-confidence independent claim | ChatGPT `citation_presentation` (SISTRIX/Ahrefs) — live ledger |
| Controlled observation, distinct from vendor docs | `web/lib/mechanics-fixtures.ts` (issue #10 lane deferred; no production controlled-observation claim exists yet) — renders "Directly observed" with a distinct tone |
| Conflicting / reconciled case | 28 inline reconciliation records on the real ChatGPT citation claim; fixture conflict renders "Compare the contradicting evidence" |

## 4. Reuse, not reimplementation

- Reconciliation: `reconciliation_index` wraps the tested `reconcile_persisted`
  unchanged; the UI joins on `claim_id` only.
- Evidence projection: the trust UI renders `dimension_view` fields verbatim; no
  claim, confidence or conflict is computed in the browser.

## 5. Review-hardening pass (frontier findings F1–F5)

- **F1 (freshness frozen by the cache).** Freshness is now derived at
  serialization time from the persisted `observed_at`, using the shared read-model
  helper — never baked into the cached projection. Verified live:
  `evidence with rationale: 15 without: 0`, freshness values `fresh · 0/1/3d`.
- **F2 (per-request O(n²) reconciliation).** The index is cached on the same
  ledger token the projection uses (`cached_reconciliation_index`), and the
  read path is confirmed pure (no session/commit/engine) by test. Live
  `/mechanics` ≈ 0.07–0.1 s.
- **F3 (unexercised Postgres branch).** Added a real-Postgres test for the
  `jsonb ?|` alias filter; a claim stored under `deepseek` is found by
  `surface=deepseek-chat`.
- **F4 (why-confidence absent on the existing ledger).** The read path now derives
  the rationale from the persisted row via the one confidence implementation, so
  every claim explains itself today — no empty-rationale placeholder in the
  deployed dataset (verified: 15/15 evidenced claims carry a rationale).
- **F5 (duplicated freshness thresholds).** One `freshness_of` implementation in
  `observations` (`FRESHNESS_THRESHOLDS`) is now called by both the claim view and
  the mechanics projection.

## 6. Second review pass (DELTA findings)

- **DELTA-1 (label/rationale disagreement).** The read path now returns the
  `derived_label` a synthesised rationale actually supports alongside the stored
  label; the UI renders "this rationale was re-derived … and supports X, while the
  claim is recorded as Y" when the two differ, instead of implying agreement.
  Found live: 6 ChatGPT claims are recorded as `medium` but re-derive as `low` —
  the trust layer now says so explicitly.
- **DELTA-2 (explainer ≠ record path).** `explain_persisted_confidence` now counts
  a metric's *value* quote (not every field quote), returns 0.5 "no metric values"
  for a metric-less claim, unwraps `{"known":..}`/provenanced envelopes, and is
  covered by a full inputs+rationale parity test against `assess_confidence`.
- **DELTA-3 (weak verification).** The "no DB writes" check is now behavioural
  (ledger opened read-only; a write would raise), and CI fails if the
  Postgres-dialect alias test silently skips.

## 7. Honest limitations

- No production `controlled_observation` claim exists yet (issue #10 is
  deferred), so that class is proven structurally via the recorded fixture, not
  on live data. Stated rather than implied.
- In-place claim corrections are bounded by the mechanics cache TTL (unchanged
  from #56).
