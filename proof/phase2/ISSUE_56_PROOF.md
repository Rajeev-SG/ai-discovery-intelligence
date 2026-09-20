# Issue #56 — canonical mechanics ontology + evidence contract: product proof

Generated from the **real production claim ledger** (32 validated claims across 35 registry surfaces).
Raw captures stay private; every value below is copied from a validated claim.

Dimensions: 13 (search_trigger, retrieval_provider, query_rewrite, crawling_indexing_controls, freshness_recrawl, candidate_selection_reranking, citation_presentation, shopping_product_feed, local_retrieval, social_community_retrieval, mode_region_differences, answer_type, marketer_controllable_inputs).

## 1. Complete ChatGPT mechanics payload (real evidence)

Coverage: **5/13 evidenced (known 5, partial 0, conflicting 0, unknown 8)**

| dimension | state | evidence class | confidence | statement |
|---|---|---|---|---|
| search_trigger | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| retrieval_provider | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| query_rewrite | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| crawling_indexing_controls | known | official_documentation | medium | It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. |
| freshness_recrawl | known | official_documentation | medium | It can take approximately 24 hours for OpenAI's systems to adjust for search results after a site's robots.txt update. |
| candidate_selection_reranking | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| citation_presentation | known | independent_research | medium | The share of ChatGPT responses with at least one inline image embedding from images.openai.com rose from approximately 1 |
| shopping_product_feed | known | independent_research | medium | Initial observations of ChatGPT ads were based on three days of data when first published on July 15, and updated on Jul |
| local_retrieval | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| social_community_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| mode_region_differences | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| answer_type | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| marketer_controllable_inputs | known | independent_research | medium | Initial observations of ChatGPT ads were based on three days of data when first published on July 15, and updated on Jul |

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
| candidate_selection_reranking | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| citation_presentation | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| shopping_product_feed | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| local_retrieval | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| social_community_retrieval | unknown | — | — | No evidenced mechanics dimension maps to this surface yet; the ledger holds no claim kind that speaks to it. |
| mode_region_differences | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| answer_type | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |
| marketer_controllable_inputs | unknown | — | — | No validated claim for this surface covers this dimension. Unknown is a valid, explicit answer, not a missing value. |

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
- A market-share/audience claim lights **no** mechanics dimension.
- The vendor-documented vs independently-researched vs directly-observed distinction is carried per evidence record (`evidence_class`).
- No private snapshot path or capture text appears in any payload.
