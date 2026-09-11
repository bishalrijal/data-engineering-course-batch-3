"""
ingest.py — Stage 1: Ingestion

Reads raw tickets from a source (CSV here; swap in an API/DB call in real
life) and loads them, untouched, into the `tickets_raw` landing table with
load metadata attached. This landing copy is never modified — it's what
you'd re-run cleaning/validation against if downstream logic changes.

Full-refresh: each run truncates and reloads `tickets_raw` from the
current source file, mirroring the old behavior of overwriting
01_ingested.jsonl on every run.
"""

import csv
import datetime
from pathlib import Path

import db

ROOT = Path(__file__).resolve().parents[1]
RAW_SOURCE = ROOT / "data" / "raw" / "tickets_raw.csv"


def ingest():
    if not RAW_SOURCE.exists():
        raise FileNotFoundError(
            f"{RAW_SOURCE} not found — run `python src/generate_data.py` first."
        )

    load_ts = datetime.datetime.now(datetime.timezone.utc)
    conn = db.get_conn()
    count = 0

    with open(RAW_SOURCE, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    conn.execute("TRUNCATE tickets_raw RESTART IDENTITY")
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """INSERT INTO tickets_raw
                       (ticket_id, subject, body, category, created_at,
                        customer_email, source, ingested_at, response)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (row["ticket_id"], row["subject"], row["body"], row["category"],
                 row["created_at"], row["customer_email"], "tickets_raw.csv", load_ts,
                 row.get("response") or None),
            )
            count += 1
    conn.commit()
    conn.close()

    print(f"Ingested {count} records -> tickets_raw")
    return count


if __name__ == "__main__":
    ingest()
