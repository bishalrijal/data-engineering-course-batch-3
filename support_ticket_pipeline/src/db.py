"""
db.py — connection + schema for the Postgres/pgvector-backed pipeline.

Every stage used to read/write its own JSONL file. That's fine for a
single-node teaching pipeline but doesn't hold up in production: no
transactions, no constraints (duplicate ticket_id was checked by hand
in a Python set), no concurrent access, no querying without loading
whole files into memory. This module gives every stage a shared
Postgres connection and a schema with the constraints those checks
used to fake in application code.

Connect with env vars (defaults match docker-compose.yml):
    PGHOST=localhost PGPORT=5433 PGDATABASE=support_tickets
    PGUSER=pipeline  PGPASSWORD=pipeline
"""

import os
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

EMBED_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2 output size — pgvector needs a fixed size

SQL_DIR = Path(__file__).resolve().parent / "sql"
MIGRATIONS_DIR = SQL_DIR / "migrations"


def get_conn():
    conn = psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5433"),
        dbname=os.environ.get("PGDATABASE", "support_tickets"),
        user=os.environ.get("PGUSER", "pipeline"),
        password=os.environ.get("PGPASSWORD", "pipeline"),
        row_factory=dict_row,
    )
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def _run_sql_file(conn, path: Path, **substitutions):
    """Read a .sql file and execute it as one multi-statement script.

    `substitutions` fills `{key}` placeholders (e.g. `{EMBED_DIM}`) before
    execution — plain string substitution, not psycopg params, because a
    pgvector column's dimension is part of the type definition, not a value
    a bind parameter could carry.
    """
    sql = path.read_text()
    for key, value in substitutions.items():
        sql = sql.replace(f"{{{key}}}", str(value))
    conn.execute(sql)


def init_db():
    conn = get_conn()
    _run_sql_file(conn, SQL_DIR / "schema.sql", EMBED_DIM=EMBED_DIM)
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        _run_sql_file(conn, migration)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Schema ready.")
