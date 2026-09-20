# Canonical discovery-mechanics ontology and evidence contract (Phase 2, issue #56)

This is the canonical model that answers, per AI discovery surface: **how does
search/discovery actually work, how do we know, and what remains unknown?**

It replaces the coarse `discovery_modes` + single `retrieval_status` enum as the
*substantive* description of a surface. `config/surfaces.yaml` keeps those fields
as a registry scorecard; they are labelled "registry metadata — not evidence" in
the UI and are never treated as mechanics findings.

## Dimensions

Each surface is projected through thirteen **independent** dimensions
(`src/ai_discovery/mechanics.py`, `MECHANICS_DIMENSIONS`):

| key | meaning |
|---|---|
| `search_trigger` | when/why the surface retrieves from the live web |
| `retrieval_provider` | which index or upstream provider backs retrieval |
| `query_rewrite` | query rewrite / decomposition / fan-out |
| `crawling_indexing_controls` | crawler user-agents, robots directives, site controls |
| `freshness_recrawl` | recrawl / freshness behaviour |
| `candidate_selection_reranking` | filtering and ranking of candidates |
| `citation_presentation` | whether/how sources are shown |
| `shopping_product_feed` | product / catalogue / feed behaviour |
| `local_retrieval` | local / place retrieval |
| `social_community_retrieval` | social / forum / community sources |
| `mode_region_differences` | mode / model / account / region differences |
| `answer_type` | direct vs retrieval-backed answer |
| `marketer_controllable_inputs` | signals a marketer can change |

## States

Every dimension carries an explicit state — never a blank cell:

- `known` — at least one non-conflicting, evidenced assertion;
- `partially_known` — evidence exists but is explicitly partial/scoped;
- `conflicting` — two or more evidenced assertions disagree (both preserved);
- `unknown` — **no evidence exists**. This is a valid, explicit answer.

## Evidence contract

A non-`unknown` dimension carries an **assertion** whose text *is the ledger
claim's own statement* — the projection never re-writes or merges claims into new
prose. Each assertion links to one or more `MechanicsEvidence` records carrying:

- claim / evidence IDs (`claim_id`, plus `relates_to_claim_id` for supersession);
- source class and the derived marketer-facing **evidence class**
  (`official_documentation`, `independent_research`, `controlled_observation`);
- published / observed / effective dates;
- confidence and (where present) score;
- measurement mode, methodology notes and stated limitations;
- applicable region scope (from the claim's own stated geography — a surface's
  *registry* regions are never asserted as evidence).

## Where evidence comes from — and what it must never be

- **Only validated ledger claims.** The projection's sole input is the expanded
  claim ledger. It never reads `retrieval_status`, never reads model knowledge,
  and never invents a mechanic to fill a cell.
- **Registry metadata is not evidence.** A surface with zero claims is fully
  `unknown` even when the registry says `partially_documented`.
- **A market-share/audience claim is never mechanics.** `audience_usage`,
  `referrals_conversion` and `measurement` are non-mechanics topics: they light
  no dimension. This is the exact "looks like a market-share tracker" anti-pattern
  issue #57 names.
- **Evidence classes stay distinct.** Vendor documentation, independent research
  and controlled observation are separate `evidence_class` values, so a reader can
  tell "the vendor says" from "a study found" from "we observed".

## Topic → dimension mapping, and the content gate

A dimension is lit by a claim only through **two independent, deterministic
gates**, both reviewed in code (never a model judgement at request time):

1. **Inherent topic** (`DIMENSION_TOPICS`) — the topic *is* the mechanic. Only
   `retrieval_index` and `crawler_index_policy` are inherent here.
2. **Content-gated signal** (`CLAIM_SIGNALS`) — a coarse topic (citations,
   commerce, optimisation) may light a dimension only when the claim's own
   statement/metric text matches a stated pattern. A citation *share* number has
   no such pattern, so it lights nothing; a claim that says sources are shown
   `inline`/`per response` lights `citation_presentation`.

This is deliberate: a coarse topic must never masquerade as a mechanic. The
content gate is the honest answer to "does this claim actually assert how the
surface works?" — and it drops the ChatGPT evidenced-dimension count from a naive
6/13 to a truthful **4/13** on the current production ledger.

## Methodology completeness (null is not "absent")

Each evidence record carries `methodology_completeness` (`not_stated` / `sparse` /
`detailed`). A null methodology field is **unstated**, never "verified absent" —
consumers must not read null as a negative finding.

## Alias attribution is auditable

Each evidence record carries both `claimed_surface_value` (as the claim stored it)
and `canonical_surface_id` (what it resolved to), so an aliased attachment is
traceable end-to-end from the payload.

## Performance

`GET /mechanics` caches the projection in-process, keyed by a ledger token
(claim count + newest `observed_at`) with a short TTL, so an unchanged ledger is
never re-projected while a write always invalidates the cache.

## Surface-id resolution (read-time only)

Extraction emits a surface name as the source page wrote it (`deepseek`,
`naver-ai-tab`). `SURFACE_ALIASES` resolves those to canonical registry ids **at
read time**; stored claims are append-only and are never rewritten. Values that
are not surfaces at all (a category like `answer-engines`, a cited domain like
`reddit`) are never coerced — they are reported in
`GET /mechanics → unmapped_claim_surfaces` as visible data drift.

## Read API

- `GET /mechanics` — the marketer-safe projection for every registry surface,
  plus the drift diagnostic. No private snapshot data, no capture text.
- `GET /surfaces/{surface_id}/mechanics` — one surface; an unknown surface id
  returns an explicit `unknown_surface` state, never a fabricated projection.

## Projection rule (no invented certainty)

1. A dimension with no mapped, validated claim → `unknown` with an explanatory note.
2. Claims that carry an explicit `contradicts`/`supersedes` (or are `contested`)
   → `conflicting`.
3. A claim marked `watch` → `partially_known`.
4. Otherwise → `known`.

## Acceptance evidence

See `proof/phase2/ISSUE_56_PROOF.md`: a complete real ChatGPT mechanics payload and
a deliberately under-documented surface (`deepseek-chat`) whose unknowns remain
explicit rather than inferred, both generated from the production ledger.
