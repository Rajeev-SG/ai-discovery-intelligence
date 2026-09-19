-- Migration: claim ledger (issue #3) — verified by tests/test_migration.py
--
-- Additive only. Depends on the issue #2 tables (source, evidence_item) for the
-- two deferred foreign keys below; enable both at issue-#2 integration.
-- source_id FK is likewise deferred; no live REFERENCES exists in this file.
--
-- History is append-only: `claim.statement` / methodology are never UPDATEd in
-- place. A new capture writes a new `claim_evidence` row; a materially changed
-- assertion gets a new `claim_id` with `relationship` + `supersedes_claim_id`.

BEGIN;

CREATE TABLE study (
    study_id            varchar(32) PRIMARY KEY,
    source_id           varchar(120) NOT NULL, -- FK to source(id) deferred to issue-#2 integration
    publisher           varchar(200) NOT NULL,
    url                 text NOT NULL,
    canonical_url       text NOT NULL,
    source_class        varchar(60) NOT NULL,
    title               text,
    measurement_mode    varchar(40) NOT NULL,
    metric_family       varchar(120),
    denominator         text,
    prompt_universe     text,
    sample_size         text,           -- NULL means unknown; never a placeholder 0
    unit_of_analysis    text,
    time_window         text,
    geography           varchar(60),
    geography_basis     varchar(30) NOT NULL DEFAULT 'not_stated',
    language            varchar(30),
    language_basis      varchar(30) NOT NULL DEFAULT 'not_stated',
    limitations         jsonb NOT NULL DEFAULT '[]'::jsonb,
    methodology_notes   text,
    extraction_version  varchar(40) NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_study_source_id ON study (source_id);

CREATE TABLE claim (
    claim_id            varchar(32) PRIMARY KEY,   -- sha256(source|topic|statement)[:32]
    study_id            varchar(32) NOT NULL REFERENCES study(study_id) ON DELETE CASCADE,
    source_id           varchar(120) NOT NULL,
    topic               varchar(40) NOT NULL CHECK (topic IN (
                            'audience_usage','retrieval_index','citations_sources',
                            'crawler_index_policy','referrals_conversion','commerce_ads',
                            'measurement','optimisation_implication')),
    statement           text NOT NULL,
    surfaces            jsonb NOT NULL DEFAULT '[]'::jsonb,
    status              varchar(30) NOT NULL DEFAULT 'current',
    relationship        varchar(30) NOT NULL DEFAULT 'new',
    supersedes_claim_id varchar(32) REFERENCES claim(claim_id),
    confidence          varchar(20) NOT NULL DEFAULT 'medium',
    extraction_method   varchar(30) NOT NULL CHECK (extraction_method IN ('deterministic_parser','llm_proposal')),
    extraction_tool     varchar(80) NOT NULL,
    extraction_version  varchar(40) NOT NULL,
    rule_id             varchar(80),
    -- LLM extraction is never evidence: an llm_proposal row must be human-reviewed.
    human_reviewed      boolean NOT NULL DEFAULT false,
    published_at        timestamptz,
    published_at_source varchar(30),
    modified_at         timestamptz,
    measured_window     text,
    observed_at         timestamptz NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_claim_llm_reviewed CHECK (
        extraction_method <> 'llm_proposal' OR human_reviewed),
    CONSTRAINT ck_claim_supersede CHECK (
        relationship = 'new' OR supersedes_claim_id IS NOT NULL),
    CONSTRAINT ck_claim_supersede_new CHECK (
        relationship <> 'new' OR supersedes_claim_id IS NULL)
);
CREATE INDEX ix_claim_source_id ON claim (source_id);
CREATE INDEX ix_claim_topic ON claim (topic);
CREATE INDEX ix_claim_status ON claim (status);
CREATE INDEX ix_claim_observed_at ON claim (observed_at);

CREATE TABLE claim_metric (
    id          bigserial PRIMARY KEY,
    claim_id    varchar(32) NOT NULL REFERENCES claim(claim_id) ON DELETE CASCADE,
    metric_id   varchar(60) NOT NULL,
    label       varchar(160) NOT NULL,
    comparator  varchar(20) NOT NULL DEFAULT 'exact',
    definition  text NOT NULL,
    -- NULL means "unknown", which is a first-class state (issue #25).
    value_text  text,
    value_number double precision,
    unit        varchar(40) NOT NULL,
    "window"    text NOT NULL,
    scope       text NOT NULL,
    CONSTRAINT uq_claim_metric UNIQUE (claim_id, metric_id)
);

CREATE TABLE claim_locator (
    id            bigserial PRIMARY KEY,
    claim_id      varchar(32) NOT NULL REFERENCES claim(claim_id) ON DELETE CASCADE,
    field_path    varchar(200) NOT NULL,
    locator_kind  varchar(30) NOT NULL CHECK (locator_kind IN (
                      'verbatim_quote','jsonld_field','table_row','page_stamp','section')),
    quote         text,
    selector      text,
    note          text,
    CONSTRAINT uq_claim_locator_field UNIQUE (claim_id, field_path),
    CONSTRAINT ck_claim_locator_pointer CHECK (quote IS NOT NULL OR selector IS NOT NULL)
);

CREATE TABLE claim_evidence (
    id             bigserial PRIMARY KEY,
    claim_id       varchar(32) NOT NULL REFERENCES claim(claim_id) ON DELETE CASCADE,
    -- evidence_id    varchar(40) REFERENCES evidence_item(id) ON DELETE SET NULL,  -- enable at #2 integration
    evidence_id    varchar(40),
    url            text NOT NULL,
    canonical_url  text NOT NULL,
    capture_hash   varchar(64) NOT NULL,
    raw_sha256     varchar(64),
    snapshot_path  text,
    http_status    integer,
    robots_allowed boolean,
    fetched_at     timestamptz NOT NULL,
    recorded_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_claim_capture UNIQUE (claim_id, capture_hash)
);
CREATE INDEX ix_claim_evidence_canonical_url ON claim_evidence (canonical_url);
CREATE INDEX ix_claim_evidence_capture_hash ON claim_evidence (capture_hash);

COMMIT;
