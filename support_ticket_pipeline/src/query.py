"""
query.py — Stage 6: Query and serving layer

Simple CLI: type a support question, get back the most semantically
similar past tickets. This is the "serving" layer of the architecture —
in a real system this logic would sit behind a REST endpoint instead
of a CLI loop.

Usage:
    python src/query.py "I was charged twice this month"
    python src/query.py "login not working" --category login --top_k 3
    python src/query.py   (no args -> interactive mode)
"""

import argparse

from embed import embed_query
from vector_store import VectorStore


def print_results(query, results):
    print(f'\nQuery: "{query}"')
    if not results:
        print("  No matches found.")
        return
    for i, r in enumerate(results, 1):
        print(f"  {i}. [{r['category']}] (score={r['score']:.3f}) ticket #{r['ticket_id']}")
        print(f"     Q: {r['text'][:120]}")
        if r.get("response"):
            print(f"     A: {r['response'][:120]}")


def run_query(query_text: str, top_k: int = 5, category: str | None = None):
    store = VectorStore()
    vec = embed_query(query_text)
    results = store.search(vec, top_k=top_k, category=category)
    print_results(query_text, results)
    return results


def main():
    parser = argparse.ArgumentParser(description="Semantic search over support tickets")
    parser.add_argument("query", nargs="?", help="Query text")
    parser.add_argument("--top_k", type=int, default=5)
    parser.add_argument("--category", default=None,
                         help="Filter to one category: billing, login, refund, bug, "
                              "feature_request, shipping")
    args = parser.parse_args()

    if args.query:
        run_query(args.query, top_k=args.top_k, category=args.category)
    else:
        print("Interactive mode — type a query, or 'quit' to exit.")
        while True:
            q = input("\n> ").strip()
            if q.lower() in ("quit", "exit", ""):
                break
            run_query(q, top_k=args.top_k, category=args.category)


if __name__ == "__main__":
    main()
