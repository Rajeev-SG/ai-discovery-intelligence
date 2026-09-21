# Issue #61 — reset the information architecture around marketer questions: product proof

Generated from the **deployed product** on the real production ledger. The
homepage now answers the four marketer questions in order; latest changes and the
weekly brief are demoted to a returning-user area.

## What shipped

- **New front door** (`web/app/page.tsx`): a marketer-language hero ("How AI
  discovery works — and what it means for you") followed by **four questions,
  answered in order**, each linking to its destination:
  1. *What AI discovery platforms exist?* → `/landscape`
  2. *How does their search and discovery work?* → `/landscape` (comparison)
  3. *How do we know — and can we trust it?* → `/surfaces` (Evidence & trust)
  4. *Why does this matter for marketers?* → `/implications`
- **Counts are live and evidence-derived** (7 landscape surfaces, 18 evidenced
  mechanics dimensions, 5 marketing implications) — the questions render explicit
  unavailable copy when a source is unreachable rather than implying zero.
- **Latest changes / weekly brief / POV demoted** below a "Returning users"
  divider; they remain fully accessible.
- **Navigation reset**: primary nav is Home / Landscape / Marketing implications /
  Explore surfaces; internal terms are demoted to secondary links — *POV* →
  **What this means**, *Reconciliation* → **Evidence reconciliation** — reachable
  but no longer driving primary navigation.
- The exhaustive registry (`/surfaces`), intelligence feed, brief, POV history,
  evidence drill-down and reconciliation all remain reachable.

## 1. Above the fold (deployed)

Screenshot: `web/proof/home-marketer-first.png`. Above the fold states what the
product is for in marketer language, orients to the major platforms, and provides
entry points into comparison and marketing implications.

## 2. The four questions, in order (live counts)

| # | Question | Live answer | Destination |
|---|---|---|---|
| 1 | What AI discovery platforms exist? | 7 major surfaces, with vendor/geography/modes/evidenced reach | /landscape |
| 2 | How does their search and discovery work? | compare retrieval/citation/crawl/commercial mechanics across surfaces | /landscape |
| 3 | How do we know — and can we trust it? | 18 evidenced mechanics dimensions with publisher/class/dates/confidence | /surfaces |
| 4 | Why does this matter for marketers? | 5 evidence-backed implications, or an explicit monitor-only state | /implications |

## 3. Acceptance evidence

- **Above the fold answers what the product is for** — marketer-language hero +
  four questions (e2e `landing renders a single, well-formed state per section`).
- **Major platforms discoverable immediately** — `/landscape` linked first.
- **Mechanics, trust and implications are first-class** — three of the four
  questions, and three of the four primary nav items.
- **Latest changes useful but not dominant** — demoted below the "Returning users"
  divider (`home-latest-title`).
- **POV/Reconciliation terminology no longer drives primary navigation** — e2e
  asserts the first four nav links contain neither "POV" nor "Reconciliation", and
  the demoted destinations remain reachable as "What this means" / "Evidence
  reconciliation".
- **Existing intelligence feed, brief, POV history, evidence and reconciliation
  remain accessible** — all still rendered (demoted) or linked.
- **Real-browser proof** — Playwright runs the whole journey on desktop + mobile.

## 4. Product proof (issue #61)

A first-time marketer can start at `/` and reach: a major platform (`/landscape`) →
how its discovery works (comparison) → evidence/trust (`/surfaces`) → marketer
implication (`/implications`), without needing repository/domain terminology.

Verification: pytest **314**, ruff clean, vitest **84**, playwright **37** live.

## 5. IA must work with unknown mechanics

The homepage and nav never depend on a mechanic being known: the implications
question states "or an explicit monitor-only state where evidence is insufficient",
and the landscape/evidence destinations show explicit unknowns. Verified live —
31 of 35 surfaces are monitor-only and the journey still holds.
