# Claim ledger (issue #3)

Converts captured source documents into auditable atomic claims **without** losing
study methodology. Claims are the unit the observation plane shows.

## Modules

| Path | Role |
| --- | --- |
| `src/ai_discovery/claim_models.py` | Pydantic domain models and the invariants (pure, no I/O) |
| `src/ai_discovery/claims.py` | Deterministic extraction rules + append-only SQLAlchemy ledger |
| `scripts/build_claim_specs.py` | Writes the extraction-rule bundle `proof/claim_ledger/claim_specs.json` |
| `scripts/build_claim_proof.py` | Fetches captures, builds the ledger, renders `proof/claim_ledger/PROOF.md` |
| `db/ledger/0001_claim_ledger.sql` | Additive Postgres DDL (Alembic-shaped) for the five ledger tables |
| `tests/test_claim_models.py`, `tests/test_claims.py` | Invariants + rule behaviour against real captures |

## Tables

`study` (methodology) · `claim` (atomic typed assertion) · `claim_metric` ·
`claim_locator` (one exact pointer per known field) · `claim_evidence`
(append-only capture history). See the DDL for column-level comments.

## Invariants enforced in code, not by convention

1. **Unknown is first-class.** A field is `Provenanced(value=None, locator=None)`.
   A value *must* carry a locator; a locator *must* not exist without a value.
   `sample_size`, `prompt_universe`, etc. are therefore `NULL` and render `_unknown_`
   when the source does not publish them - never a placeholder `0`.
2. **Every field is traceable.** `iter_provenanced()` walks the whole claim and writes
   a `claim_locator` row per known field path (methodology, each metric's
   definition/value/unit/window/scope). Extraction refuses to emit a claim whose
   declared quote is absent from the capture, so a fabricated number cannot be stored.
3. **Dates stay distinct.** `published_at`, `modified_at`, `measured_window` and
   `observed_at` are four separate fields; a validator rejects `modified_at < published_at`
   and a naive `observed_at`. Confirmed distinct on the real pages: e.g. Similarweb
   published 2026-05-14, modified 2026-06-11, measured ~Apr 2026, observed 2026-09-16.
4. **LLM extraction is never evidence.** `ExtractionProvenance` rejects
   `method="llm_proposal"` unless `human_reviewed=True`, and the DDL carries the same
   `CHECK`. v1 is deterministic-parser only; if prose inference is added it must come
   through Instructor + Pydantic structured output and land as a human-reviewed row.
5. **Claim identity is content-addressed.** `claim_id = sha256(source_id|topic|statement)[:32]`,
   so re-extracting the same assertion from the same source is the same claim. A changed
   assertion gets a new id with `relationship` + `supersedes_claim_id`.
6. **History is append-only.** Nothing is updated in place. A re-capture (new
   `capture_hash`) adds a `claim_evidence` row and leaves prior rows untouched.

## Claim topics

`audience_usage`, `retrieval_index`, `citations_sources`, `crawler_index_policy`,
`referrals_conversion`, `commerce_ads`, `measurement`, `optimisation_implication`.

## Product proof (real, not synthetic)

`proof/claim_ledger/PROOF.md` is generated from live public captures:

| Claim | Publisher | Topic | Published | Notes |
| --- | --- | --- | --- | --- |
| Similarweb AI-chatbot visit share | Similarweb | audience_usage | 2026-05-14 | ChatGPT 52.7% / Gemini 27.3% / Claude 8.9%; sample unknown |
| SISTRIX weekly citation drift | SISTRIX | citations_sources | 2026-05-01 | 82,619 prompts, 17 weeks, six countries; ChatGPT ~74%, AI Mode ~56% |
| Yandex AI answers monthly users | Yandex | audience_usage | 2026-09-14 | >49M/month; measured month unnamed |
| NAVER AI Tab beta | NAVER | referrals_conversion | 2026-06-26 | 4M cumulative users, card CTR >20%, 50M daily main-page visitors (kept separate) |

The rendered view is *expanded*: each claim shows source, distinct dates, full
methodology (mode, denominator, sample, window, geography with basis), every metric,
and the per-field quote table - not just the summarised sentence. Raw HTML captures
stay private under `proof/claim_ledger/captures/` (git-ignored); the committed manifest
records each `raw_sha256`, HTTP status and fetch time.

Reproduce:

```bash
python3 scripts/build_claim_proof.py            # live fetch -> ledger -> PROOF.md
python3 scripts/build_claim_proof.py --from-captures
python3 -m pytest tests/test_claim_models.py tests/test_claims.py -q
```

## Integration contract (for the parent, after issue #2 checkpoints)

This work is deliberately decoupled so it can land before #2's `evidence_item` table:

- **`Base`.** `claims.py` imports `Base` from `ai_discovery.models` (owned by #2) and
  only falls back to a local declarative `Base` when that module is absent. At
  integration, delete the fallback; the ledger DDL is unchanged.
- **`Study.source_id`** should become `VARCHAR(120) REFERENCES source(id) ON DELETE SET NULL`.
- **`ClaimEvidence.evidence_id`** should become `VARCHAR(40) REFERENCES evidence_item(id) ON DELETE SET NULL`
  (the migration ships this line commented out, ready to enable). `capture_hash` matches
  `EvidenceItem.capture_hash` (sha256 of extracted text); `raw_sha256` matches
  `EvidenceItem.raw_sha256`.
- **Alembic.** Move `db/ledger/0001_claim_ledger.sql` into the revision chain after #2's
  evidence migration; do not renumber #2's revision.
- **API/UI (parent-owned).** `load_expanded_claims(engine)` already returns the expanded
  view (claim + methodology + metrics + provenance + evidence) that the observation
  endpoint/UI should serve; wire it to the API rather than re-deriving the shape.
- **Not touched here (parent coordinates):** `src/ai_discovery/models.py`, `api.py`,
  `pyproject.toml`, root `README.md`, CI. This branch adds no dependencies beyond the
  stack #2 already adopts.

## Not yet covered

- LLM/prose extraction (deterministic rules only).
- Cross-claim reconciliation states (`material_conflict`, `possible_transient_change`)
  and the Reddit conflict example - issue #4.
- Change events / living POV revisions - issues #5 and #7.
- Paywalled or JS-only sources, and any fetching that needs a browser.
