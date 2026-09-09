-- Base schema for the support-ticket pipeline. Applied by db.init_db() at
-- the top of every stage script, so any stage is runnable standalone with
-- no separate setup step to remember. Every statement is idempotent
-- (IF NOT EXISTS) — safe to run on every process start.
--
-- {EMBED_DIM} is substituted by db.py before this file is executed.

-- Landing zone: raw records exactly as ingested, never mutated downstream.
-- Full-refresh per run (TRUNCATE + INSERT), same semantics as the old
-- 01_ingested.jsonl being overwritten on every run.
CREATE TABLE IF NOT EXISTS tickets_raw (
    id SERIAL PRIMARY KEY,
    ticket_id TEXT,
    subject TEXT,
    body TEXT,
    category TEXT,
    created_at TEXT,
    customer_email TEXT,
    source TEXT,
    ingested_at TIMESTAMPTZ,
    response TEXT
);

-- Validated + PII-redacted records. ticket_id is a real primary key here —
-- the database rejects a duplicate instead of a Python set having to catch
-- it, and a rerun safely upserts rather than reprocessing everything.
CREATE TABLE IF NOT EXISTS tickets_validated (
    ticket_id TEXT PRIMARY KEY,
    subject TEXT,
    body TEXT,
    category TEXT,
    created_at TEXT,
    customer_email TEXT,
    had_pii BOOLEAN,
    validated_at TIMESTAMPTZ,
    response TEXT
);

-- Log of rejected records + why, one run's worth (full-refresh per run).
CREATE TABLE IF NOT EXISTS tickets_rejected (
    id SERIAL PRIMARY KEY,
    reason TEXT,
    record JSONB,
    rejected_at TIMESTAMPTZ
);

-- Cleaned, embedding-ready text chunks.
CREATE TABLE IF NOT EXISTS ticket_chunks (
    chunk_id TEXT PRIMARY KEY,
    ticket_id TEXT,
    text TEXT,
    category TEXT,
    created_at TEXT,
    had_html BOOLEAN,
    response TEXT
);

-- Vectors, filterable metadata alongside them (no separate vector-DB
-- process to keep in sync — one system, one transaction).
CREATE TABLE IF NOT EXISTS ticket_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES ticket_chunks(chunk_id) ON DELETE CASCADE,
    ticket_id TEXT,
    category TEXT,
    created_at TEXT,
    embedding vector({EMBED_DIM})
);

-- HNSW index for cosine-distance search. Not load-bearing at ~300 rows
-- (a sequential scan is instant either way) but this is exactly where a
-- real deployment would need it, so it's here for realism.
CREATE INDEX IF NOT EXISTS ticket_embeddings_hnsw_idx
    ON ticket_embeddings USING hnsw (embedding vector_cosine_ops);
