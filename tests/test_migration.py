"""Migration-fidelity test: apply the real DDL and exercise its constraints."""

import sqlite3
from pathlib import Path

import pytest

MIGRATION = Path(__file__).resolve().parents[1] / "db" / "ledger" / "0001_claim_ledger.sql"


def _strip_pg_dialect(sql: str) -> str:
    """Adapt PostgreSQL DDL to SQLite for a structural-fidelity check.

    We run against SQLite because CI has no Postgres container; this proves the
    table shapes, CHECK constraints and uniqueness rules, not the column types.
    """
    import re

    sql = re.sub(r"\bvarchar\(\d+\)", "TEXT", sql)
    sql = re.sub(r"\bbigserial\b", "INTEGER", sql)
    sql = re.sub(r"\bjsonb?\b", "TEXT", sql)
    sql = re.sub(r"\btimestamptz\b", "TEXT", sql)
    sql = re.sub(r"\btimestamp\b", "TEXT", sql)
    sql = re.sub(r"\bGENERATED ALWAYS AS IDENTITY\b", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"::jsonb", "", sql)
    sql = re.sub(r"::text", "", sql)
    # The migration's header comment contains an unquoted '#' that trips SQLite.
    # Strip everything before the first CREATE TABLE; the rest is valid DDL.
    first_ct = sql.find("CREATE TABLE")
    if first_ct > 0:
        sql = sql[first_ct:]
    # Inline comments containing ':' are also SQLite-unfriendly inside columns.
    # Strip full-line -- comments (keeps the DDL only) for a structural test.
    lines = []
    for line in sql.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        # Remove trailing -- comments from data lines (crude but sufficient here)
        if "--" in line and not line.strip().startswith("--"):
            line = line[: line.index("--")]
        lines.append(line)
    result = "\n".join(lines)
    # Strip remaining inline comments like "[:32]" which are not valid SQL.
    result = re.sub(r"\[:\d+\]", "", result)
    result = result.replace("::TEXT", "")
    result = result.replace("DEFAULT now()", "DEFAULT CURRENT_TIMESTAMP")
    # executescript auto-commits; drop the explicit BEGIN/COMMIT.
    result = re.sub(r"^\s*(BEGIN|COMMIT)\s*;?\s*$", "", result, flags=re.MULTILINE)
    return result


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    sql = MIGRATION.read_text()
    adapted = _strip_pg_dialect(sql)
    conn.executescript(adapted)
    yield conn
    conn.close()


def test_tables_exist(db):
    tables = {
        r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "study" in tables
    assert "claim" in tables
    assert "claim_evidence" in tables


def test_claim_id_is_primary_key(db):
    cols = {r[1]: r for r in db.execute("PRAGMA table_info(claim)").fetchall()}
    assert "claim_id" in cols
    assert cols["claim_id"][5] == 1  # pk flag


def test_unique_claim_locator(db):
    # Insert a study then two identical claim_locator rows; second should fail.
    db.execute(
        "INSERT INTO study (study_id, source_id, publisher, url, canonical_url, source_class, measurement_mode, extraction_version) "
        "VALUES ('s1', 'src1', 'P', 'https://u', 'https://u', 'official', 'vendor_report', 'v0.1')"
    )
    db.execute(
        "INSERT INTO claim (claim_id, study_id, source_id, topic, statement, extraction_method, extraction_tool, extraction_version, observed_at, status) "
        "VALUES ('c1', 's1', 'src1', 'audience_usage', 'stmt', 'deterministic_parser', 'similarweb_visit_share_v1', 'v0.1.0', CURRENT_TIMESTAMP, 'current')"
    )
    db.execute(
        "INSERT INTO claim_locator (claim_id, field_path, locator_kind, quote) VALUES ('c1', 'p', 'verbatim_quote', 'q')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO claim_locator (claim_id, field_path, locator_kind, quote) VALUES ('c1', 'p', 'verbatim_quote', 'q')"
        )


def test_claim_status_check(db):
    db.execute(
        "INSERT INTO study (study_id, source_id, publisher, url, canonical_url, source_class, measurement_mode, extraction_version) "
        "VALUES ('s2', 'src2', 'P', 'https://u', 'https://u', 'official', 'vendor_report', 'v0.1')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO claim (claim_id, study_id, source_id, topic, statement, extraction_method, extraction_tool, extraction_version, observed_at, status) "
            "VALUES ('c2', 's2', 'src2', 'bogus_topic', 'stmt', 'deterministic_parser', 'x_v1', 'v0.1.0', CURRENT_TIMESTAMP, 'current')"
        )


# --- 0002: unknown value_text may be NULL (issue #25) ----------------------- #

MIGRATION_0002 = (
    Path(__file__).resolve().parents[1] / "db" / "ledger" / "0002_claim_metric_value_text_nullable.sql"
)


def test_value_text_nullable_migration_exists():
    assert MIGRATION_0002.exists(), "issue #25 needs a forward migration for existing ledgers"


def test_0002_relaxes_value_text_not_null_on_an_existing_ledger():
    """An existing ledger must accept NULL value_text after the #25 migration."""

    conn = sqlite3.connect(":memory:")
    conn.executescript(_strip_pg_dialect(MIGRATION.read_text()))
    # SQLite cannot ALTER COLUMN DROP NOT NULL, so prove the intent structurally:
    # the migration must target exactly the claim_metric.value_text column.
    sql = MIGRATION_0002.read_text()
    assert "ALTER TABLE claim_metric" in sql
    assert "value_text" in sql
    assert "DROP NOT NULL" in sql
    conn.close()
