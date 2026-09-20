# Phase 2 — corpus rebalance toward discovery mechanics (issue #57)

The pre-#57 production corpus was audience/usage-heavy and looked like a
market-share tracker. This change shifts the corpus toward **how AI discovery
actually works**, using evidence already present in the committed real captures
but not yet extracted.

## What we added — and why it is real

`scripts/build_mechanics_claims.py` authors deterministic claim specs over the
**real, committed captures** in `proof/claim_ledger/captures/`. The existing
extraction lane (`ai_discovery.claims.extract_claim`) re-verifies every declared
quote against the capture bytes and refuses a claim whose quote is absent, so no
value is invented. Every new claim is tagged with a canonical mechanics topic.

| new claim | topic | surface(s) | source class |
|---|---|---|---|
| Google AI Mode/Overviews may use query fan-out | retrieval_index | google-ai-mode, google-ai-overviews | official |
| AI Overviews trigger only when additive to classic Search | retrieval_index | google-ai-overviews | official |
| Google surfaces more/diverse supporting links than classic search | citations_sources | google-ai-mode, google-ai-overviews | official |
| AI Mode vs AI Overviews may use different models/techniques | retrieval_index | google-ai-mode, google-ai-overviews | official |
| ChatGPT-User is user-triggered, not automatic crawling | crawler_index_policy | chatgpt | official |
| ChatGPT-User does not control Search eligibility | crawler_index_policy | chatgpt | official |
| ~50% of retrieved ChatGPT URLs are cited | citations_sources | chatgpt | independent |
| Average cited ChatGPT page is ~500 days old | citations_sources | chatgpt | independent |
| ChatGPT retrieval returns title/snippet/URL/ID before opening a page | retrieval_index | chatgpt | independent |
| Perplexity benchmarks first-stage retrieval (Q2D-Web) | retrieval_index | perplexity | official |

## Before → after

See `proof/phase2/CORPUS_DISTRIBUTION.md` and `proof/phase2/MECHANICS_COVERAGE_MATRIX.md`.

- `retrieval_index`: **0 → 5** (was completely empty).
- `crawler_index_policy`: **1 → 3**.
- `citations_sources`: **10 → 13** (with retrieval-gate content, not just shares).
- `audience_usage`: **16 → 16** — **no new share/audience claim added**.
- Evidenced mechanics (surface × dimension) cells: **6 → 18** of 208.
- Change events derived from the new claims: **10** (retrieval/index change ×5,
  citation-source shift ×3, crawler policy ×2).

## Source-class and regional diversity

New claims span `official` (Google, OpenAI, Perplexity) and
`visibility_research` (Ahrefs), keeping source-class diversity visible. No new
regional claim was added because the real captures for the CN/KR/JP/RU surfaces
carry no mechanics evidence; inventing one would violate the evidence contract.
That gap is the explicit target of #10 (controlled observation).

## Honest boundary

- Topic→dimension gating (from #56) means a citation *share* still lights no
  dimension; only claims that assert a gate/presentation/trigger mechanic do.
- Regional mechanics remain `unknown` because public evidence does not exist yet
  — recorded, not papered over.
- Ingesting *new* sources (rather than extracting already-captured pages) is
  deliberately out of scope here: the highest-value cheapest win was extracting
  mechanics evidence the corpus already held.
