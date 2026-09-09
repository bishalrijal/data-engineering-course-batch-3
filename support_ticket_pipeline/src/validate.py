"""
validate.py — Stage 2: Validation layer

Sits between ingestion and cleaning. Catches bad records BEFORE they get
transformed and embedded, and keeps a log of what was rejected and why —
so failures are visible instead of silently corrupting the pipeline.

Three checks, run in order:
  1. Schema validation   - required fields present, correct-ish types
  2. Content validation   - empty/near-empty text, duplicate IDs
  3. PII validation       - emails/phones/card numbers in free text get redacted

Valid records -> tickets_validated (upserted on ticket_id — a rerun after
                 a source fix updates the row instead of reprocessing
                 everything or silently duplicating it)
Rejected records + reason -> tickets_rejected (full-refresh per run)
"""

import datetime
import json
import re

import db
from html_utils import strip_html

REQUIRED_FIELDS = ["ticket_id", "body", "category"]
MIN_BODY_LENGTH = 8  # characters, after stripping whitespace

CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
PHONE_RE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def check_schema(record: dict) -> str | None:
    for field in REQUIRED_FIELDS:
        if not record.get(field) or str(record.get(field)).strip() == "":
            return f"missing_required_field:{field}"
    return None


def check_content(record: dict, seen_ids: set) -> str | None:
    # Judge length on the actual text, not the raw HTML — a near-empty body
    # wrapped in a couple of tags (e.g. "<p>asdkjh</p>") must still be caught.
    body = strip_html(record.get("body", "")).strip()
    if len(body) < MIN_BODY_LENGTH:
        return "body_too_short_or_garbled"
    if record["ticket_id"] in seen_ids:
        return "duplicate_ticket_id"
    return None


def redact_pii(text: str) -> tuple[str, bool]:
    """Redact card numbers, phone numbers, and emails. Returns (clean_text, had_pii)."""
    had_pii = False
    for pattern, placeholder in [
        (CARD_RE, "[REDACTED_CARD]"),
        (PHONE_RE, "[REDACTED_PHONE]"),
        (EMAIL_RE, "[REDACTED_EMAIL]"),
    ]:
        if pattern.search(text):
            had_pii = True
            text = pattern.sub(placeholder, text)
    return text, had_pii


def validate():
    db.init_db()
    conn = db.get_conn()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT ticket_id, subject, body, category, created_at, customer_email, response "
            "FROM tickets_raw ORDER BY id"
        )
        raw_records = cur.fetchall()

    seen_ids = set()
    valid_count = 0
    rejected_count = 0
    pii_redacted_count = 0
    now = datetime.datetime.now(datetime.timezone.utc)

    conn.execute("TRUNCATE tickets_rejected RESTART IDENTITY")

    with conn.cursor() as cur:
        for record in raw_records:
            reason = check_schema(record)
            if reason is None:
                reason = check_content(record, seen_ids)

            if reason:
                cur.execute(
                    "INSERT INTO tickets_rejected (reason, record, rejected_at) "
                    "VALUES (%s, %s, %s)",
                    (reason, json.dumps(record), now),
                )
                rejected_count += 1
                continue

            seen_ids.add(record["ticket_id"])

            clean_body, had_pii_body = redact_pii(record["body"])
            # Redact the agent's response too — a resolution note can reference
            # the same account details ("refunded the charge on card ...") the
            # customer's own message did.
            clean_response, had_pii_response = redact_pii(record.get("response") or "")
            had_pii = had_pii_body or had_pii_response
            if had_pii:
                pii_redacted_count += 1

            cur.execute(
                """INSERT INTO tickets_validated
                       (ticket_id, subject, body, category, created_at,
                        customer_email, had_pii, validated_at, response)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (ticket_id) DO UPDATE SET
                       subject = EXCLUDED.subject,
                       body = EXCLUDED.body,
                       category = EXCLUDED.category,
                       created_at = EXCLUDED.created_at,
                       customer_email = EXCLUDED.customer_email,
                       had_pii = EXCLUDED.had_pii,
                       validated_at = EXCLUDED.validated_at,
                       response = EXCLUDED.response""",
                (record["ticket_id"], record["subject"], clean_body, record["category"],
                 record["created_at"], record["customer_email"], had_pii, now, clean_response),
            )
            valid_count += 1

    conn.commit()
    conn.close()

    print(f"Validation complete: {valid_count} valid, {rejected_count} rejected, "
          f"{pii_redacted_count} records had PII redacted.")
    print("  Valid    -> tickets_validated")
    print("  Rejected -> tickets_rejected")
    return valid_count, rejected_count


if __name__ == "__main__":
    validate()
