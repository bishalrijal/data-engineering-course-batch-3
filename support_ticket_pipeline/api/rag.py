"""
rag.py — retrieval-augmented generation over the support ticket pipeline.

Reuses the existing pipeline's Stage 5/6 code as-is (embed_query,
VectorStore) instead of re-implementing retrieval here — the API is just a
new "serving" front-end on top of the same vector store query.py already
talks to. The only new piece is Stage 7: handing the retrieved chunks to
an LLM (Gemini Flash) instead of printing them to a terminal.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from google import genai

# src/ modules use bare imports (`import db`, `from embed import ...`), so
# they need to be on sys.path rather than imported as a package.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from embed import embed_query  # noqa: E402
from vector_store import VectorStore  # noqa: E402

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

PROMPT_TEMPLATE = """You are a support assistant. Answer the user's question using ONLY \
the context below, which is drawn from past support tickets and how they were actually \
resolved. Prefer restating the resolution that applies, not just acknowledging the \
question. If the context doesn't contain enough information to answer, say so plainly \
instead of guessing. Be concise.

Context:
{context}

Question: {query}

Answer:"""


@lru_cache(maxsize=1)
def _get_store() -> VectorStore:
    return VectorStore()


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/apikey and put it in your .env file."
        )
    return genai.Client(api_key=api_key)


def _build_prompt(query: str, chunks: list[dict]) -> str:
    if not chunks:
        context = "No related tickets were found."
    else:
        entries = []
        for c in chunks:
            entry = f"[Ticket #{c['ticket_id']} | category={c['category']}]\nQ: {c['text']}"
            if c.get("response"):
                entry += f"\nResolution: {c['response']}"
            entries.append(entry)
        context = "\n\n".join(entries)
    return PROMPT_TEMPLATE.format(context=context, query=query)


def answer_query(query: str, top_k: int = 5, category: Optional[str] = None) -> dict:
    store = _get_store()
    vec = embed_query(query)
    chunks = store.search(vec, top_k=top_k, category=category)

    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL, contents=_build_prompt(query, chunks)
    )

    return {
        "answer": response.text,
        "sources": [
            {
                "ticket_id": c["ticket_id"],
                "category": c["category"],
                "score": round(float(c["score"]), 4),
                "text": c["text"][:300],
                "response": (c.get("response") or "")[:300],
            }
            for c in chunks
        ],
    }
