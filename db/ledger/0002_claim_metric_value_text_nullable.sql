-- Migration: allow an unknown claim_metric.value_text to persist as NULL (issue #25)
--
-- Additive. Depends on db/ledger/0001_claim_ledger.sql.
--
-- 0001 declared `value_text text NOT NULL`, so a ledger created before this fix
-- rejects the NULL that "unknown is a first-class state" requires: persist now
-- writes NULL for an unknown value (matching value_number) instead of the
-- literal string "None". Existing rows are untouched; only the constraint is
-- relaxed. Safe to re-run.

BEGIN;

ALTER TABLE claim_metric
    ALTER COLUMN value_text DROP NOT NULL;

COMMIT;
