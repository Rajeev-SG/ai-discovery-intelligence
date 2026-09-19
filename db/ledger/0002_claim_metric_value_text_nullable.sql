-- Migration: unknown claim_metric.value_text persists as NULL (issue #25)
--
-- 0001 already declares value_text nullable, so a freshly created ledger is
-- correct on its own. This file exists for ledgers that were created by an
-- earlier 0001 that declared `value_text text NOT NULL` (and for any environment
-- still carrying the sentinel string the old writer produced):
--
--   * DROP NOT NULL  - forward-only, a no-op if the column is already nullable;
--   * UPDATE ...     - one-time backfill of the literal "None" the pre-fix
--                      writer stored for an unknown value, to a real NULL.
--
-- Safe to re-run on either the old or the new shape.

BEGIN;

ALTER TABLE claim_metric
    ALTER COLUMN value_text DROP NOT NULL;

UPDATE claim_metric
   SET value_text = NULL
 WHERE value_text = 'None'
   AND value_number IS NULL;

COMMIT;
