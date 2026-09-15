# 07 — Maintain the source-backed SEO/AEO/GEO POV and changelog automatically

## Outcome
A stable executive POV that changes only when evidence warrants it.

## Requirements
- Generate/maintain the structure in `docs/EXECUTIVE_POV.md` as product data, not a free-running weekly essay.
- Each proposition has a stable ID, current text, confidence, supporting/contradicting evidence IDs, last-reviewed date and revision history.
- New events can propose a POV revision; deterministic editorial/materiality rules gate automatic adoption.
- Changes must be surgical: do not rewrite unrelated sections for stylistic reasons.
- Generate a readable changelog containing old statement, new statement, reason and evidence IDs.
- Support “no POV change this week” as a correct outcome.

## Real product proof required
Use a real evidence change to update exactly one POV proposition and show the before/after diff + changelog. Also show at least one current event that does **not** alter the POV.
