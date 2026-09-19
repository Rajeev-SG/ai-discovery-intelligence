-- Migration: persist derived-confidence inputs on claim (issue #28A)
--
-- 0001 already carries these columns, so a fresh ledger needs no migration. This
-- file exists for ledgers created before that change. Additive and safe to re-run.

BEGIN;

ALTER TABLE claim ADD COLUMN IF NOT EXISTS confidence_score double precision;
ALTER TABLE claim ADD COLUMN IF NOT EXISTS confidence_inputs jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE claim ADD COLUMN IF NOT EXISTS confidence_rationale jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMIT;
