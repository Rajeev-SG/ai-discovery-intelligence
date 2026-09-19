-- Migration: record deterministic capture verification distinctly from human review
-- (issue #9).
--
-- 0001 carries the column on a fresh ledger. This file exists for ledgers created
-- before it, and relaxes the llm-provenance CHECK so an llm_proposal row may be
-- admitted when every locator was deterministically verified against the capture
-- bytes — without falsely claiming a human reviewed the model output. Additive and
-- safe to re-run.
--
-- Note: ADD COLUMN IF NOT EXISTS and DROP CONSTRAINT IF EXISTS are supported by
-- PostgreSQL 9.6+.

BEGIN;

ALTER TABLE claim ADD COLUMN IF NOT EXISTS verified_against_capture boolean NOT NULL DEFAULT false;

ALTER TABLE claim DROP CONSTRAINT IF EXISTS ck_claim_llm_reviewed;
ALTER TABLE claim ADD CONSTRAINT ck_claim_llm_reviewed CHECK (
    extraction_method <> 'llm_proposal' OR human_reviewed OR verified_against_capture);

COMMIT;
