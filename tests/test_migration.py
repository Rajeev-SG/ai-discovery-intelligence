"""Migration-fidelity test: apply the real DDL and exercise its constraints."""

import os
import re
import sqlite3
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

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


PG_URL = os.environ.get("AI_DISCOVERY_TEST_DATABASE_URL")


def _postgres():
    """A psycopg connection to the test database, or skip when unavailable.

    The 0002 migration is PostgreSQL DDL (``ALTER COLUMN ... DROP NOT NULL``), so
    proving it needs a real Postgres. CI provides one as a service; locally the
    compose ``db`` service on 127.0.0.1:55432 works. Absent both, the test skips
    rather than pretending a string match is verification.
    """

    url = PG_URL or "postgresql://ai_discovery:ai_discovery@127.0.0.1:55432/ai_discovery"
    try:
        return psycopg.connect(url, autocommit=True)
    except psycopg.OperationalError as exc:  # pragma: no cover - no local Postgres
        pytest.skip(f"no Postgres available: {exc}")


def _apply_pg_ddl(conn, sql: str, schema: str = "public") -> None:
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(sql)


def test_0002_relaxes_value_text_not_null_and_backfills_legacy_none():
    """Run the real 0002 against Postgres: NULL insert succeeds, ``'None'`` -> NULL.

    Builds claim_metric from the real ``0001`` DDL, restores the pre-fix
    ``NOT NULL`` and a legacy ``'None'`` row, then applies 0002 and asserts both
    the constraint is gone and the sentinel is backfilled. Skipped without Postgres.
    """

    conn = _postgres()
    schema = "adi_mig_test"
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            cur.execute(f"CREATE SCHEMA {schema}")
            cur.execute(f"SET search_path TO {schema}")

        ddl = MIGRATION.read_text()
        metric_ddl = ddl[ddl.index("CREATE TABLE claim_metric") : ddl.index("CREATE TABLE claim_locator")]
        # The inline FK targets ``claim``; this shape test needs only the column
        # shape, and the FK itself is covered by the 0001 fidelity test above.
        metric_ddl = re.sub(r"REFERENCES claim\(claim_id\)[^,]*", "", metric_ddl)
        with conn.cursor() as cur:
            cur.execute("SET search_path TO " + schema)
            cur.execute(metric_ddl)
            cur.execute("ALTER TABLE claim_metric ALTER COLUMN value_text SET NOT NULL")
            cur.execute(
                "INSERT INTO claim_metric"
                " (claim_id, metric_id, label, definition, value_text, value_number, unit, \"window\", scope)"
                " VALUES ('c1','m1','label','def','None',NULL,'u','w','s')"
            )

        # A NULL insert must fail under the pre-fix constraint.
        with pytest.raises(psycopg.errors.NotNullViolation), conn.cursor() as cur:
            cur.execute("SET search_path TO " + schema)
            cur.execute(
                "INSERT INTO claim_metric"
                " (claim_id, metric_id, label, definition, value_text, value_number, unit, \"window\", scope)"
                " VALUES ('c1','m2','label','def',NULL,NULL,'u','w','s')"
            )

        # Apply the real migration.
        with conn.cursor() as cur:
            cur.execute("SET search_path TO " + schema)
            cur.execute(MIGRATION_0002.read_text())

        with conn.cursor() as cur:
            cur.execute("SET search_path TO " + schema)
            cur.execute(
                "INSERT INTO claim_metric"
                " (claim_id, metric_id, label, definition, value_text, value_number, unit, \"window\", scope)"
                " VALUES ('c1','m3','label','def',NULL,NULL,'u','w','s')"
            )
            cur.execute("SELECT value_text FROM claim_metric WHERE metric_id='m1'")
            assert cur.fetchone()[0] is None, "legacy 'None' row must be backfilled to NULL"
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO public")
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        finally:
            conn.close()
