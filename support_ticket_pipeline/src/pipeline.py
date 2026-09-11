"""
pipeline.py — runs the full architecture end to end.

Day 1 (ingestion -> validation -> cleaning):
    python src/pipeline.py --day 1

Day 2 (embedding -> vector store, adds on top of Day 1's output):
    python src/pipeline.py --day 2

Full run:
    python src/pipeline.py
"""

import argparse

import ingest
import validate
import clean_transform
import embed


def run_day1():
    print("=== Stage 1: Ingestion ===")
    ingest.ingest()
    print("\n=== Stage 2: Validation ===")
    validate.validate()
    print("\n=== Stage 3: Cleaning & transformation ===")
    clean_transform.transform()


def run_day2():
    print("=== Stage 4: Embedding generation ===")
    embed.build_and_save()
    print("\nPipeline ready. Try: python src/query.py \"your question here\"")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", choices=["1", "2"], default=None)
    args = parser.parse_args()

    if args.day == "1":
        run_day1()
    elif args.day == "2":
        run_day2()
    else:
        run_day1()
        print()
        run_day2()


if __name__ == "__main__":
    main()
