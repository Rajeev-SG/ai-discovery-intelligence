-- Migration: change_event + brief_snapshot tables (issue #23)
--
-- 0001 carries the claim ledger only. This adds the two read-path tables the
-- observation plane needs: persisted change events and weekly brief snapshots.
-- Additive and safe to re-run.

BEGIN;

CREATE TABLE IF NOT EXISTS change_event (
    id             varchar(12) PRIMARY KEY,
    event_type     varchar(40) NOT NULL,
    title          text NOT NULL,
    surfaces       jsonb NOT NULL DEFAULT '[]'::jsonb,
    dedupe_key     varchar(200),
    payload        text NOT NULL,
    observed_at    timestamptz NOT NULL,
    published_at   timestamptz,
    effective_from timestamptz
);
CREATE INDEX IF NOT EXISTS ix_change_event_event_type ON change_event (event_type);
CREATE INDEX IF NOT EXISTS ix_change_event_dedupe_key ON change_event (dedupe_key);
CREATE INDEX IF NOT EXISTS ix_change_event_observed_at ON change_event (observed_at);

CREATE TABLE IF NOT EXISTS brief_snapshot (
    id           bigserial PRIMARY KEY,
    generated_at timestamptz NOT NULL DEFAULT now(),
    payload      text NOT NULL
);

COMMIT;
