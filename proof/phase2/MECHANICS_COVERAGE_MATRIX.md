# Issue #57 — mechanics coverage matrix

Core surfaces × 13 canonical dimensions (contract from #56).
K = known, P = partial, C = conflicting, · = unknown (explicit).

**Evidenced cells: 21 of 208 (10%).**

| surface | trigger | provider | rewrite | crawl | fresh | rank | cite | shop | local | social | mode | answer | control | evidenced |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| chatgpt | K | K | K | K | K | · | K | · | · | · | · | · | K | 7/13 |
| google-gemini | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| google-ai-mode | K | K | K | · | · | · | K | · | · | · | · | · | · | 4/13 |
| google-ai-overviews | K | K | K | · | · | · | K | · | · | · | · | · | · | 4/13 |
| microsoft-copilot | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| bing-copilot-search | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| claude | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| perplexity | K | K | K | · | · | · | · | · | · | · | · | · | · | 3/13 |
| deepseek-chat | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| grok | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| meta-ai | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| doubao | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| qwen-consumer | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| kimi | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| baidu-ai-search | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/13 |
| naver-ai | K | K | K | · | · | · | · | · | · | · | · | · | · | 3/13 |

Legend — dimensions:
- `search_trigger` — trigger
- `retrieval_provider` — provider
- `query_rewrite` — rewrite
- `crawling_indexing_controls` — crawl
- `freshness_recrawl` — fresh
- `candidate_selection_reranking` — rank
- `citation_presentation` — cite
- `shopping_product_feed` — shop
- `local_retrieval` — local
- `social_community_retrieval` — social
- `mode_region_differences` — mode
- `answer_type` — answer
- `marketer_controllable_inputs` — control
