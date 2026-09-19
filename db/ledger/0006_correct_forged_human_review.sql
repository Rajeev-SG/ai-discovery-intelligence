-- Migration: correct rows mislabelled human_reviewed by the pre-fix automated
-- lane (issue #9).
--
-- A defect in the acquisition lane called the extractor with human_reviewed=True
-- on unattended LLM output, so any llm_proposal claim it wrote carries
-- human_reviewed=true even though no person read it. This migration corrects
-- exactly those rows — the automated lane is the only writer that sets
-- extraction_tool='ai_discovery.semantic' with method='llm_proposal', and no
-- code path lets a human set human_reviewed on that tool — by clearing
-- human_reviewed and setting the honest flag the lane actually establishes
-- (every locator verified against the capture bytes). An operator can audit the
-- affected rows first with the SELECT. Idempotent and safe to re-run.

BEGIN;

-- Audit (run standalone to inspect before applying):
--   SELECT claim_id, statement FROM claim
--    WHERE extraction_method = 'llm_proposal'
--      AND extraction_tool = 'ai_discovery.semantic'
--      AND human_reviewed;

UPDATE claim
   SET human_reviewed = false,
       verified_against_capture = true
 WHERE extraction_method = 'llm_proposal'
   AND extraction_tool = 'ai_discovery.semantic'
   AND human_reviewed = true;

COMMIT;
