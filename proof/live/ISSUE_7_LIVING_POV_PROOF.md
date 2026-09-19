# Issue #7 — living POV proof

Attached evidence for closing #7, produced from the real production ledger (the
same validated claims the live observation plane reads), not fixtures.

## What "the POV is product data" means here

- `pov/state.yaml` — the POV as data: stable proposition ids, each with an owner
  topic set, a stable editorial `base_text`, and one evidence bullet per owned
  topic. Plus an append-only `changelog`.
- `config/pov_policy.yaml` — the deterministic editorial gate: minimum event
  significance, minimum claim-confidence label, topic ownership, and a stated
  per-topic significance profile. No model decides.
- `scripts/build_pov.py` — regenerates `docs/EXECUTIVE_POV.md` (only the block
  between `<!-- pov:generated:start -->` / `end -->`) and `pov/CHANGELOG.md` from
  the ledger. Deterministic and idempotent.

## Proof 1 — one real evidence change updates exactly one proposition

Run against the live ledger (Dagster→Crawl4AI→Instructor claim `0b187a5b…`,
event `9f7e8c586b05`, topic `crawler_index_policy`, confidence `medium`):

```
$ python scripts/build_pov.py
POV: 4 propositions, 1 adopted, 0 skipped, 1 changelog entries
  pov-retrieval-systems: medium (1 bullets)
  pov-channel-prioritisation: unresolved (0 bullets)
  pov-commerce-ads: unresolved (0 bullets)
  pov-measurement: unresolved (0 bullets)
```

Exactly one proposition changed (`pov-retrieval-systems`); the other three are
byte-identical to before. The changelog entry (`pov/CHANGELOG.md`):

```
## 2026-09-19 — pov-retrieval-systems

- **Reason:** material crawler_index_policy change: significance 3.67 >= 3.50, confidence medium
- **Event:** `9f7e8c586b05`
- **Evidence:** `0b187a5b6f942c1d2a3fcb12285238e5`
- **Significance:** 3.67 · **Confidence:** medium

**Before**
Each surface reaches the live web through a different retrieval and citation stack, ...

**After**
Each surface reaches the live web through a different retrieval and citation stack, ...
- It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. (evidence 0b187a5b…; 2026-09-19; medium)
```

Re-running the generator is a no-op (idempotent): `diff` of `pov/state.yaml`
before/after a second run is empty — "no POV change this run" is visible, not
hidden.

## Proof 2 — a current event correctly produces no POV change

Three independent, real skip paths, all covered by tests in
`tests/test_pov.py`:

1. **Topic a proposition does not own.** A `commerce_ads` event (no proposition
   owns that topic in a state whose propositions are retrieval/channel) is
   skipped: `no proposition owns topic 'commerce_ads'`.
2. **An implication is not a change.** An `optimisation_implication` claim is
   excluded by the gate (its stated significance profile is below the bar), so it
   never moves the POV.
3. **Weak evidence.** A `low`-confidence claim is skipped for being below
   `min_confidence`; a claim under the significance bar is skipped for that.

These are deterministic gate outcomes, not model judgement; the CI step
`Living POV is deterministic and gated (issue #7)` asserts both an adoption and a
correct skip on every run.

## Integrity

The gate is evidence-derived: confidence comes from the claim's own
`confidence` (itself derived from evidence, never a model label), and
significance comes from the stated per-topic profile in
`config/pov_policy.yaml`. Adopting a change is surgical — one proposition's
bullet is replaced, nothing else is rewritten. 11 POV tests; whole suite green.
