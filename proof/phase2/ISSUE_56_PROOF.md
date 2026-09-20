# Issue #56 — canonical mechanics ontology + evidence contract: product proof

Generated from the **real production claim ledger** (32 validated claims across 35 registry surfaces).
Raw captures stay private; every value below is copied from a validated claim.

Dimensions: 13 (search_trigger, retrieval_provider, query_rewrite, crawling_indexing_controls, freshness_recrawl, candidate_selection_reranking, citation_presentation, shopping_product_feed, local_retrieval, social_community_retrieval, mode_region_differences, answer_type, marketer_controllable_inputs).

## 1. Complete ChatGPT mechanics payload (real evidence)

Coverage: **4/13 evidenced (known 4, partial 0, conflicting 0, unknown 9)**

| dimension | state | evidence class | confidence | statement |
|---|---|---|---|---|
| search_trigger | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| retrieval_provider | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| query_rewrite | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| crawling_indexing_controls | known | official_documentation | medium | It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. |
| freshness_recrawl | known | official_documentation | medium | It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. |
| candidate_selection_reranking | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| citation_presentation | known | independent_research | medium | The share of ChatGPT responses with at least one inline image embedding from images.openai.com rose from approximately 1 |
| shopping_product_feed | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| local_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| social_community_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| mode_region_differences | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| answer_type | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| marketer_controllable_inputs | known | official_documentation | medium | It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. |

Full payload: `proof/phase2/chatgpt_mechanics.json`.

## 2. Under-documented surface — unknowns stay explicit

`deepseek-chat` (registry status: under_documented). Real claims exist for this surface (audience only), so no mechanics dimension is evidenced and every dimension is an explicit `unknown` - never inferred from the registry.

Coverage: **0/13 evidenced (known 0, partial 0, conflicting 0, unknown 13)**

| dimension | state | evidence class | confidence | statement |
|---|---|---|---|---|
| search_trigger | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| retrieval_provider | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| query_rewrite | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| crawling_indexing_controls | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| freshness_recrawl | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| candidate_selection_reranking | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| citation_presentation | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| shopping_product_feed | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| local_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| social_community_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| mode_region_differences | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| answer_type | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| marketer_controllable_inputs | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |

Full payload: `proof/phase2/deepseek_mechanics.json`.

## 3. Surface-id drift surfaced (not silently coerced)

Claim surface values that are not registry surfaces (and not aliases) are reported as data drift, never attached to a real surface:

```json
{
  "answer-engines": [
    "63c1770ffc1c6ac089036c30383a8f1c"
  ],
  "reddit": [
    "8bb8d5a3d280ba07aea2ba74aa07c10f"
  ]
}
```

## 4. Invariants demonstrated

- A dimension with no supporting claim is `unknown` with a note, not blank.
- A market-share/audience claim lights **no** mechanics dimension. A citation-*share* claim lights no dimension either: a dimension needs an inherent topic or a content-gated signal (review F1).
- The vendor-documented vs independently-researched vs directly-observed distinction is carried per evidence record (`evidence_class`).
- Each evidence record carries its original surface value and canonical id (auditable alias attachment, F4) and a methodology-completeness flag so a null field is never read as 'verified absent' (F5).
- No private snapshot path or capture text appears in any payload.

## 5. Conflicting / partial dimensions

The current production ledger holds **no** conflicting or superseded claims (every claim is `relationship='new'`, `status='current'`), so `conflicting`/`partially_known` are 0 across the corpus. That state is reachable and is proven end-to-end by `tests/test_mechanics.py::test_multi_source_ledger_projects_conflict_and_supersession` over a realistic multi-source ledger, rather than being forced onto a share-only corpus.
