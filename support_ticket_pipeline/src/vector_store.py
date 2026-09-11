"""
vector_store.py — Stage 5: Vector store

Thin wrapper over the pgvector-backed `ticket_embeddings` table. Cosine
similarity search and the category filter are both pushed down into SQL
(`ORDER BY embedding <=> %s`, `WHERE category = %s`) instead of loading
every vector into a numpy array and masking client-side — the database
does the filtering and the HNSW index (see db.py) does the nearest-
neighbor search, so this scales past what fits in memory on one process.
"""

from typing import Optional

import numpy as np

import db


class VectorStore:
    def __init__(self):
        self.conn = db.get_conn()
        # Read-only connection, cached for the life of the process (see
        # api/rag.py::_get_store()) — autocommit so a search() call doesn't
        # leave the connection idle-in-transaction afterward, holding a lock
        # that would block DDL (e.g. a schema migration) on the same tables.
        self.conn.autocommit = True

    def search(self, query_vector: np.ndarray, top_k: int = 5, category: Optional[str] = None):
        sql = """
            SELECT c.chunk_id, c.ticket_id, c.text, c.category, c.created_at, c.response,
                   1 - (e.embedding <=> %(qvec)s) AS score
            FROM ticket_embeddings e
            JOIN ticket_chunks c USING (chunk_id)
        """
        params = {"qvec": query_vector, "top_k": top_k}
        if category:
            sql += " WHERE c.category = %(category)s"
            params["category"] = category
        sql += " ORDER BY e.embedding <=> %(qvec)s LIMIT %(top_k)s"

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
