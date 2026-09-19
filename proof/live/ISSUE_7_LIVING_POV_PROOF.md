# Issue #7 — living POV proof

Attached evidence for closing #7, produced from the real production ledger (the
same validated claims the live observation plane reads), not fixtures.

## What "the POV is product data" means here

- `pov/state.yaml` — the POV as data: stable proposition ids, each with an owner
  topic set, a stable editorial `base_text`, separate `supporting` and
  `contradicting` evidence lists, a `last_reviewed` stamp, an append-only
  `changelog`, and a durable `processed_events` watermark.
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
  pov-retrieval-systems: medium (1 supporting, 0 contradicting)
  pov-channel-prioritisation: unresolved (0 supporting, 0 contradicting)
  pov-commerce-ads: unresolved (0 supporting, 0 contradicting)
  pov-measurement: unresolved (0 supporting, 0 contradicting)
```

Exactly one proposition changed; the other three are byte-identical. The
changelog entry (`pov/CHANGELOG.md`) carries the before/after statements, the
reason, significance/confidence and the evidence id:

```
## 2026-09-19 — pov-retrieval-systems
- **Reason:** material crawler_index_policy change: significance 3.67 >= 3.50, confidence medium (first-seen quantified claim)
- **Event:** `9f7e8c586b05`
- **Evidence:** `0b187a5b6f942c1d2a3fcb12285238e5`
```

Re-running the generator is a no-op: `diff` of `pov/state.yaml` and
`pov/CHANGELOG.md` before/after a second run is empty. This idempotency is durable
(the `processed_events` watermark), so it holds however many events share a topic.

## Proof 2 — a current event correctly produces no POV change

Three real, deterministic skip paths, each covered in `tests/test_pov.py`:

1. **Topic a proposition does not own.** A `commerce_ads` event is skipped:
   `no proposition owns topic 'commerce_ads'`.
2. **A repeat is not a change.** Re-reporting the incumbent value scores
   magnitude 0 and is skipped: `no material change (value unchanged vs incumbent)`.
3. **Weak evidence.** A `low`-confidence claim is skipped for being below
   `min_confidence`; an `optimisation_implication` (an implication, not a change)
   is excluded by its stated significance profile.

## Review-driven hardening (frontier review of #44)

- **Durable idempotency.** A `processed_events` watermark in `pov/state.yaml`
  makes a full-history replay converge to the same state with zero new changelog
  entries, even with two qualifying events on one topic.
- **Event-specific significance.** Magnitude is now the relative change of the
  claim's value against the incumbent (0 for a repeat), and breadth/persistence
  are derived from surfaces and claim status, so the gate distinguishes a
  material change from a trivial quantified one.
- **Supporting/contradicting evidence.** Bullets carry a polarity; contradictions
  are retained and cap the proposition at `low` confidence (marked *contested*)
  rather than silently overwriting support.
- **Claim statement precedence.** The bullet quotes the validated claim
  statement, not the event's ingest title.
- **Validated confidence + no dead config.** `to_pov_confidence` rejects unknown
  labels loudly; the unused `max_propositions_per_event` knob was removed.

## Integrity

Confidence is the claim's own evidence-derived label (validated into the POV
vocabulary, never a model label); significance uses stated per-topic editorial
weights plus claim-derived magnitude/breadth/persistence. Edits are surgical. 15
POV tests; whole suite green.
