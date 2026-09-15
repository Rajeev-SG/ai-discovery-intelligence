# Retrieval and discovery taxonomy

The product must describe **how a consumer surface discovers information**, not merely which model brand powers it.

## Separate dimensions

### Consumer surface
The interface/channel a person actually uses: ChatGPT, Gemini, Google AI Mode, DeepSeek Chat, Doubao, NAVER AI Tab, etc.

### Trigger
When does external retrieval happen: always, conditional, explicit user toggle, tool/mode dependent, unknown.

### Query transformation
Does the surface use the user query directly, generate query fan-outs, rewrite/translate it, issue parallel searches, search social/native corpora, or use another documented transformation?

### Upstream retrieval source
Classify separately and evidence each claim:
- first-party web/search index;
- third-party search provider;
- hybrid first/third-party retrieval;
- platform-native corpus/social search;
- structured partner/product feed;
- direct site crawl/fetch;
- unknown/undocumented.

Do not infer provider identity from result similarity.

### Crawl/index controls
Track documented crawler/user-agent names, robots behaviour, index eligibility, opt-out controls and whether training crawl differs from search/retrieval crawl.

### Selection/reranking
Where evidence exists, track candidate retrieval vs final source selection/reranking. A retrieved URL is not necessarily cited.

### Citation/presentation
Track whether citations are inline, footnotes, source cards, hidden, absent or mode-dependent; domain vs URL volatility; source diversity; and commercial modules.

### Commerce/local/action layer
Track product feeds, shopping cards, retailer/merchant integrations, local/place sources, booking/action integrations and ads separately from general web retrieval.

### Consumer UI vs API
Never transfer a finding from an API/web-search tool to the consumer product without explicit evidence. Store `surface`, `mode`, `client`, `account_state`, `region` and `observed_at` when direct observations exist.

## Observation-plane columns

Default concise columns should map to these concepts:

`Surface | Geography | Audience priority | Retrieval trigger | Search/index source | Query fan-out | Crawl controls | Citation/source behaviour | Commerce/ads/actions | Latest material change | Confidence | Last verified`

Each cell may expand into evidence history and methodology. Unknown is a first-class value.
