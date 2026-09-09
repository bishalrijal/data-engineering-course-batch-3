"""
clean_transform.py — Stage 3: Cleaning and transformation

Takes validated records and prepares them for embedding:
  - Strip HTML markup (real ticket bodies come from rich-text/WYSIWYG
    forms — <p>, <strong>, links, entities, malformed/unclosed tags —
    and TF-IDF over raw HTML would just treat tag soup as vocabulary)
  - Drop quoted reply chains and <script>/<style> content entirely
  - Strip email signatures and client boilerplate ("Sent from my iPhone", etc.)
  - Normalize whitespace/casing artifacts
  - Combine subject + body into a single `text` field
  - Split that text into one or more chunks (the unit we actually embed)
  - Replace the ticket's rows in ticket_chunks with the fresh chunk set
"""

import re

import db
from html_utils import strip_html

# Most ticket bodies are short enough to stay a single chunk — this only
# does real work once a ticket (or its history) runs long enough that
# stuffing it into one embedding vector would blur together multiple
# unrelated points. 400 chars is small on purpose for a teaching pipeline;
# a production system embedding longer documents would size this closer to
# the embedding model's actual context window.
CHUNK_MAX_CHARS = 400
CHUNK_OVERLAP_CHARS = 60

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

BOILERPLATE_PATTERNS = [
    re.compile(r"sent from my iphone", re.IGNORECASE),
    re.compile(r"sent from my android", re.IGNORECASE),
    re.compile(r"sent from yahoo mail.*", re.IGNORECASE),
    re.compile(r"get outlook for ios", re.IGNORECASE),
]

# Cuts the body at the first sign-off — everything after is a signature
# (name, title, mailto: link, ...), not ticket content. Two shapes: a
# salutation phrase ("Best regards,") or a bare "--" delimiter line.
SIGNOFF_PHRASE_RE = re.compile(
    r"\b(best regards|kind regards|warm regards|many thanks|thanks|cheers|sincerely)\s*,",
    re.IGNORECASE,
)
SIGNOFF_DELIM_RE = re.compile(r"\s--\s")

WHITESPACE_RE = re.compile(r"\s+")


def strip_signature(text: str) -> str:
    candidates = [
        m.start()
        for m in (SIGNOFF_PHRASE_RE.search(text), SIGNOFF_DELIM_RE.search(text))
        if m and m.start() > 15  # don't nuke short bodies that happen to contain "thanks"
    ]
    if candidates:
        return text[: min(candidates)].strip()
    return text


def clean_text(text: str) -> str:
    text = strip_html(text)
    # Normalize whitespace before pattern-matching below: get_text() inserts
    # its separator at every tag boundary, so a phrase split across tags
    # (e.g. "Sent <strong>from</strong> my iPhone") comes out with doubled
    # spaces that a single-space regex would silently fail to match.
    text = WHITESPACE_RE.sub(" ", text).strip()
    text = strip_signature(text)
    for pattern in BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    text = text.replace("pls", "please").replace("Pls", "Please")
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Word-boundary split, used only when a single sentence alone exceeds
    max_chars (no punctuation to break on otherwise)."""
    pieces, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) > max_chars and current:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_text(
    text: str, max_chars: int = CHUNK_MAX_CHARS, overlap_chars: int = CHUNK_OVERLAP_CHARS
) -> list[str]:
    """Split text into chunks of at most max_chars, breaking on sentence
    boundaries where possible, with a bit of overlap between consecutive
    chunks so a point made right at a split isn't context-free on either
    side of it.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""
    for sentence in SENTENCE_SPLIT_RE.split(text):
        if len(sentence) > max_chars:
            for piece in _hard_split(sentence, max_chars):
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(piece)
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)

    overlapped = [chunks[0]]
    for prev, chunk in zip(chunks, chunks[1:]):
        overlapped.append(f"{prev[-overlap_chars:]} {chunk}".strip())
    return overlapped


def transform():
    db.init_db()
    conn = db.get_conn()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT ticket_id, subject, body, category, created_at, response "
            "FROM tickets_validated"
        )
        records = cur.fetchall()

    count = 0
    chunk_count = 0
    html_count = 0

    with conn.cursor() as cur:
        for record in records:
            raw_body = record.get("body") or ""
            had_html = "<" in raw_body and ">" in raw_body
            if had_html:
                html_count += 1

            subject = clean_text(record.get("subject") or "")
            body = clean_text(raw_body)
            combined_text = f"{subject}. {body}" if subject else body
            # The response is already plain text (see generate_data.py), but run
            # it through clean_text() anyway for whitespace normalization — same
            # treatment every other embedded field gets. Not itself chunked: it
            # rides along on every chunk of this ticket as RAG context, not as
            # something we search over.
            response = clean_text(record.get("response") or "")

            chunks = chunk_text(combined_text)

            # A ticket's chunk *count* can change between runs (e.g. an edit
            # makes the body cross the chunk-size threshold), so a plain
            # ON CONFLICT (chunk_id) upsert can't detect a chunk that no
            # longer exists — it would just sit there stale. Delete this
            # ticket's chunks first and re-insert the fresh set; still only
            # touches the one ticket that changed, not a full-table
            # TRUNCATE. ON DELETE CASCADE takes the matching rows in
            # ticket_embeddings with it.
            cur.execute(
                "DELETE FROM ticket_chunks WHERE ticket_id = %s", (record["ticket_id"],)
            )
            for i, chunk in enumerate(chunks):
                cur.execute(
                    """INSERT INTO ticket_chunks
                           (chunk_id, ticket_id, text, category, created_at, had_html, response)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (f"{record['ticket_id']}-{i}", record["ticket_id"], chunk,
                     record.get("category", "unknown"), record.get("created_at"), had_html,
                     response),
                )
                chunk_count += 1
            count += 1

    conn.commit()
    conn.close()

    print(f"Cleaned and transformed {count} records -> {chunk_count} chunks in ticket_chunks")
    print(f"  {html_count} records had HTML markup stripped")
    return count


if __name__ == "__main__":
    transform()
