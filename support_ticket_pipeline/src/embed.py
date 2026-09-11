"""
embed.py — Stage 4: Embedding generation

Turns cleaned text into vectors using a real, open-source neural embedding
model — sentence-transformers/all-MiniLM-L6-v2 — instead of TF-IDF+SVD.

TF-IDF only ever captures lexical overlap: it can't score "can't log in"
and "password reset broken" as similar, because they don't share a word.
A model trained specifically for sentence similarity places paraphrases
close together in vector space regardless of shared vocabulary, which is
what "semantic" search is actually supposed to deliver.

The model is downloaded once from the Hugging Face Hub and cached locally
(~90MB, in ~/.cache/huggingface) — no API key and no per-call cost, and no
network access needed on any run after the first. Swapping to a different
or larger open model, or to a hosted embeddings API, only means changing
MODEL_NAME/embed_query() here — vector_store.py and query.py only ever
expect a fixed-size vector back.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

import db

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = db.EMBED_DIM  # 384 — must match the pgvector column in db.py


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def load_chunks(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT chunk_id, ticket_id, text, category, created_at FROM ticket_chunks")
        return cur.fetchall()


def build_and_save():
    conn = db.get_conn()
    chunks = load_chunks(conn)
    if not chunks:
        raise RuntimeError("ticket_chunks is empty — run clean_transform.py first.")

    texts = [c["text"] for c in chunks]
    model = _get_model()
    # normalize_embeddings=True: L2-normalized vectors, so pgvector's cosine
    # distance operator (<=>) and a plain dot product agree.
    embeddings = model.encode(texts, batch_size=32, normalize_embeddings=True)

    with conn.cursor() as cur:
        for chunk, vec in zip(chunks, embeddings):
            cur.execute(
                """INSERT INTO ticket_embeddings
                       (chunk_id, ticket_id, category, created_at, embedding)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (chunk_id) DO UPDATE SET
                       category = EXCLUDED.category,
                       created_at = EXCLUDED.created_at,
                       embedding = EXCLUDED.embedding""",
                (chunk["chunk_id"], chunk["ticket_id"], chunk["category"],
                 chunk["created_at"], vec.astype(np.float32)),
            )
    conn.commit()
    conn.close()

    print(f"Embedded {len(chunks)} chunks into {embeddings.shape[1]}-dim vectors "
          f"using {MODEL_NAME}")
    print("  Saved -> ticket_embeddings (pgvector)")
    return embeddings.shape


def embed_query(query_text: str) -> np.ndarray:
    """Embed a single new query with the same model used at index time."""
    model = _get_model()
    vec = model.encode([query_text], normalize_embeddings=True)[0]
    return vec.astype(np.float32)


if __name__ == "__main__":
    build_and_save()
