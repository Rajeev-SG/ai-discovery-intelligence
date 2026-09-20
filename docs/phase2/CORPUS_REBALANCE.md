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
| ChatGPT fan-out length doubled in 4 months (20M+ fan-outs) | retrieval_index | chatgpt | independent |
| AI Overviews appear in 86% of 500k sampled prompts | retrieval_index | google-ai-overviews | independent |
| Google AI Mode: own domain in only 43% of brand queries | citations_sources | google-ai-mode | independent |
| NAVER AI Tab surfaces Map info + reservations in answers | retrieval_index | naver-ai | official |
| NAVER AI Tab connects answers to shopping/place/actions | retrieval_index | naver-ai | official |
| Yandex open-sourced Alice AI Search Pretrain (Search answers) | retrieval_index | yandex-ai-search | official |

## Before → after

See `proof/phase2/CORPUS_DISTRIBUTION.md` and `proof/phase2/MECHANICS_COVERAGE_MATRIX.md`.

- `retrieval_index`: **0 → 9** (was completely empty).
- `crawler_index_policy`: **1 → 3**.
- `citations_sources`: **10 → 14** (with retrieval-gate/age content, not just shares).
- `audience_usage`: **16 → 16** — **no new share/audience claim added**.
- Evidenced mechanics (surface × dimension) cells: **6 → 21** of 208.
- Core surfaces with any mechanics evidence: **1 → 6** (chatgpt, google-ai-mode,
  google-ai-overviews, perplexity, naver-ai, yandex-ai-search).
- Change events derived from the new claims: **16**.

## Operator-facing, not a one-off script

The same extraction path (`build_records()` in `scripts/build_mechanics_claims.py`)
is exposed as a Dagster asset, `mechanics_claims`, in `src/ai_discovery/pipeline.py`
(depends on `feed_items`). So the scheduled pipeline persists the quote-verified
mechanics claims and derives their change events — the CLI and the pipeline share
one code path.

## Source-class and regional diversity

New claims span `official` (Google, OpenAI, Perplexity) and
`visibility_research` (Ahrefs), keeping source-class diversity visible. No new
regional claim was added because the real captures for the CN/KR/JP/RU surfaces
carry no mechanics evidence; inventing one would violate the evidence contract.
That gap is the explicit target of #10 (controlled observation).

## Coverage is partial and stated as such

This is **not** a complete rebalance. 6 of 17 core surfaces have any mechanics
evidence; the other 11 are entirely `unknown` because **no public evidence has
been captured for them yet** — not because they were overlooked. The coverage
matrix headline states the un-evidenced count explicitly. Filling it is the job
of #10 (controlled observation) and later capture pushes, not of inference.

Two data-quality rules the review enforced:

- **No brand-name evidence.** Geography/language are set only when the capture
  actually establishes them. The NAVER press release is an English-language
  global page, so its claims carry `geography=None`/`language=None`
  (`basis='not_stated'`), not `South Korea`/`Korean` inferred from the brand.
- **Source URLs resolve to the evidence.** The new sources point at their
  specific article pages (SISTRIX AI-citation-drift article, NAVER press-release
  detail, Yandex news item); where a capture is a blog index (Peec), that
  limitation is recorded on the claims rather than presenting the index URL as
  the article.

## Honest boundary

- Topic→dimension gating (from #56) means a citation *share* still lights no
  dimension; only claims that assert a gate/presentation/trigger mechanic do.
- Regional mechanics remain `unknown` because public evidence does not exist yet
  — recorded, not papered over.
- Ingesting *new* sources (rather than extracting already-captured pages) is
  deliberately out of scope here: the highest-value cheapest win was extracting
  mechanics evidence the corpus already held.
