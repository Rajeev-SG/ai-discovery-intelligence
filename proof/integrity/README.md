# Evidence-integrity scorecard (issue #29)

`scorecard.json` is produced by `scripts/build_integrity_scorecard.py`, which runs
the **real** modules (extraction guard, unknown persistence, event dedupe,
reconciliation, weekly brief, confidence) against a checked-in fixture set. Each
check records what the production code did — nothing is hand-scored.

Run it: `uv run python scripts/build_integrity_scorecard.py` (CI runs it too; a
failure exits non-zero and fails the build).

## Checks

| check | criterion |
| --- | --- |
| fabricated claim rejected | `admitted == 0` |
| fabricated selector rejected | `admitted == 0` |
| unknown round-trips as unknown | `rendered_as_known == 0` |
| correction retained | `correction_dropped == 0` |
| contradictions preserved | `both_claims_preserved == 1`, `falsely_resolved == 0` |
| old study not a new change | `old_study_misclassified == 0` |
| brief inclusion matches expected | `mismatch == 0` |
| confidence not model-asserted | `elevated_by_model == 0` |

## Negative controls

1. **Plausible-but-unsupported figure** — `9.9M` visits with a matching (false)
   quote must be rejected.
2. **Corrected figure sharing a syndication key** — the correction must survive
   dedupe and appear in the timeline.

Removing the fabrication guard in `claim_models.Locator.present_in`, or the
`correction_retraction`/`supersedes` protection in `EventStore.dedupe`, makes the
scorecard fail — `tests/test_integrity_scorecard.py` asserts both.

## Verified vs warning

Every check carries `status: verified` (a real module made the call) or `warning`
(a hypothesis-level note), so a confirmed defect is distinguishable from a
suspicion.
