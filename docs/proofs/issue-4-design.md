# Issue 4 — methodology comparison contract (implementation in progress)

The reconciliation function compares surface, cited subject, metric definition,
denominator, geography, consumer/API mode, sampling frame, unit and measured
period **before** interpreting different numbers. Missing fields remain unknown.
It returns a separate agency interpretation with source claim/evidence IDs and
an explicit confidence adjustment. It never mutates either original claim.

- Same measurement context and value: compatible support, no automatic confidence
  boost (independence still needs assessment).
- Known mismatched contexts: methodologically incomparable, contextualises.
- Missing comparability fields: unresolved, not agreement.
- Non-overlapping periods with otherwise equal context: temporal update, not a
  disproof. The newer claim is identified independently of argument order.
- Overlapping but unequal windows: incomparable aggregates.
- Provisional observations: possible transient change rather than durable fact.
- Different values with otherwise matched contexts: contested estimates. No
  claim of statistical significance without uncertainty estimates.

## Canonical live case to integrate

The live Semrush URL reports Promptwatch's provisional decline from 3.8% to
0.5% across July/August 2026 windows. Ahrefs' living article, originally published
in 2025 and updated September 2, 2026, reports September 2026 US Brand Radar
mention share of 16.8% **among summed citations of the top sources**. These are
not directly comparable estimates. Do not infer recovery, causality, a permanent
change, or “ChatGPT stopped using Reddit”. The later observation only limits the
stronger universal claim. Sample/query counts must remain unknown if unstated.

Sources (independently inspected 2026-09-16; ingestion hash/export still pending):
- https://www.semrush.com/blog/reddits-citations-in-chatgpt-fall/
- https://ahrefs.com/blog/most-cited-domains-in-chatgpt/

## Current verification status

30 deterministic unit cases pass. Unit inputs are labelled synthetic and are
**not product acceptance proof**. Closure still requires captured canonical
source evidence, persisted ledger relationships, observation-plane drill-down,
and a fresh rendered screenshot/export after issues 2 and 3 are integrated.
# Frontier review response (2026-09-16)

The 3 findings are template placeholders with no content (Problem/Impact/Required fix all read '…').

| Finding | Resolution | Verification |
|---|---|---|
| F1 (blank) | No actionable content. Reconciliation module has 30 passing tests and ruff-clean status. | `pytest tests/ -q` |
| F2 (blank) | No actionable content. Live-source verification is documented in docs/proofs/issue-4-design.md. | Live capture /tmp/adi-reddit-research.md |
| F3 (blank) | No actionable content. No identified defect. | `ruff check src tests` |

# Issue-#4 product proof: contested Reddit/ChatGPT reconciliation. PR #11.
