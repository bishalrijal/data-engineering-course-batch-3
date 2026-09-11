# Semantic search over support tickets — working pipeline

A complete, runnable implementation of the architecture:

```
Raw data sources -> Ingestion -> Validation -> Cleaning/transformation
                  -> Embedding generation -> Vector store -> Query & serving
```

Ticket data and embeddings both live in **Postgres + pgvector** (via
Docker) — one system, real constraints, real queryability — instead of
flat JSONL/`.npy` files. Embeddings come from an open-source neural
model on Hugging Face — `sentence-transformers/all-MiniLM-L6-v2` — not
TF-IDF, so paraphrases with no words in common ("can't log in" / "password
reset broken") still land close together in vector space. The model
downloads once (~90MB) and is cached locally after that — no API key,
no per-call cost, and no network access needed on any run after the
first.

## Setup

```bash
pip install -r requirements.txt
docker compose up -d          # starts Postgres+pgvector on localhost:5433
```

The first call to `python src/pipeline.py --day 2` (or `embed.py`
directly) downloads `sentence-transformers/all-MiniLM-L6-v2` from the
Hugging Face Hub — needs network access once, then it's cached locally
and every later run is fully offline.

The pipeline connects with env vars (defaults match `docker-compose.yml`,
so you don't need to set anything for local use):

| var          | default            |
|--------------|--------------------|
| `PGHOST`     | `localhost`        |
| `PGPORT`     | `5433`             |
| `PGDATABASE` | `support_tickets`  |
| `PGUSER`     | `pipeline`         |
| `PGPASSWORD` | `pipeline`         |

Note the port: this box already runs a native Postgres on `5432` for
other coursework, so the container is mapped to `5433` to stay out of
its way. Schema creation (`CREATE EXTENSION vector`, tables, the HNSW
index) is idempotent and runs automatically at the start of every stage
— there's no separate migration step, but `python src/db.py` will just
apply it on its own if you want to run it explicitly.

## Project structure

```
support_ticket_pipeline/
├── docker-compose.yml     # Postgres + pgvector
├── data/
│   └── raw/               # generated synthetic tickets (input CSV)
├── src/
│   ├── generate_data.py   # creates the synthetic dataset
│   ├── db.py               # Postgres connection + schema (tables live here)
│   ├── ingest.py            # Stage 1: ingestion       -> tickets_raw
│   ├── validate.py           # Stage 2: validation      -> tickets_validated / tickets_rejected
│   ├── html_utils.py          # shared HTML->text helper (validate + clean both use it)
│   ├── clean_transform.py      # Stage 3: cleaning        -> ticket_chunks
│   ├── embed.py                  # Stage 4: embedding       -> ticket_embeddings (pgvector)
│   ├── vector_store.py            # Stage 5: vector store (SQL cosine search)
│   ├── query.py                    # Stage 6: query & serving (CLI)
│   └── pipeline.py                  # orchestrates all stages
└── requirements.txt
```

## Data model

```
tickets_raw          landing zone, exactly as ingested, full-refresh per run
tickets_validated     ticket_id PRIMARY KEY, PII-redacted, upserted per run
tickets_rejected       reason + full record (jsonb), full-refresh per run
ticket_chunks           one or more cleaned chunks per ticket, chunk_id = {ticket_id}-{n}
ticket_embeddings        vector(384) column + category/created_at, upserted on chunk_id
                          + an HNSW index for cosine-distance search
```

`tickets_validated` and `ticket_embeddings` are **upserted**
(`ON CONFLICT ... DO UPDATE`) rather than truncated — rerun the pipeline
after fixing a source record and only that row changes, instead of
reprocessing (or re-embedding) everything from scratch. The
duplicate-`ticket_id` rejection you'll see below is still caught by
Python during validation (so a same-run duplicate produces a
`duplicate_ticket_id` log entry rather than silently overwriting), but
the primary key backs it up as a hard constraint.

`ticket_chunks` is the one exception: since a single ticket can produce a
*variable number* of chunks (see chunking below), a plain upsert keyed on
`chunk_id` can't detect a chunk that no longer exists after an edit — it
would just sit there stale. `clean_transform.py` instead deletes a
ticket's existing chunks and re-inserts the fresh set, per ticket — still
scoped to just the one ticket that changed, not a full-table truncate.
`ON DELETE CASCADE` on `ticket_embeddings.chunk_id` takes the matching
embeddings with it.

## Day 1: Ingestion -> Validation -> Cleaning

```bash
python src/generate_data.py     # creates data/raw/tickets_raw.csv (~275 tickets,
                                 # with deliberately broken records mixed in)
python src/db.py
python src/pipeline.py --day 1  # runs ingest -> validate -> clean_transform
```

Ticket bodies are generated as **HTML**, the way a real helpdesk's
rich-text ticket form actually submits them (Zendesk/Freshdesk/Intercom
all store the body as HTML, not plain text) — `<p>`/`<strong>` tags,
`&nbsp;`/`&#39;` entities, links, bullet lists, email signatures,
quoted reply chains (`<blockquote>`), and occasional malformed/unclosed
tags or stray `<style>` blocks pasted in from a webmail client. See
`src/generate_data.py::htmlify()`.

Inspect what got rejected and why:
```bash
psql "postgresql://pipeline:pipeline@localhost:5433/support_tickets" \
     -c "SELECT reason, record->>'ticket_id' FROM tickets_rejected;"
```
You should see 4 rejected records: a missing body, a missing ticket_id,
a duplicate ticket_id, and a garbled/too-short body (`<p>asdkjh</p>` —
note that validation measures the *stripped* text length via
`html_utils.strip_html`, not the raw HTML length, otherwise a couple of
wrapper tags would be enough to sneak a near-empty body past the
length check). One valid record also has a credit card + phone number
+ email redacted — including a PII email embedded inside a `mailto:`
link — check:
```bash
psql "postgresql://pipeline:pipeline@localhost:5433/support_tickets" \
     -c "SELECT body FROM tickets_validated WHERE had_pii;"
```
for the `[REDACTED_CARD]` / `[REDACTED_PHONE]` / `[REDACTED_EMAIL]` markers.

`clean_transform.py` is what turns that HTML back into plain text
before embedding:
- `html_utils.strip_html()` parses the (possibly malformed) HTML with
  BeautifulSoup, drops `<script>`/`<style>` content and `<blockquote>`
  quoted-reply threads entirely, and returns decoded plain text —
  deliberately not a regex substitution, since regex can't reliably
  handle unclosed tags or nested markup.
- `strip_signature()` cuts the body at the first sign-off (a
  salutation phrase like "Best regards," or a bare `--` delimiter
  line), since a customer's title/name/email in a signature block is
  noise for semantic search, not ticket content.
- Whitespace is normalized *before* boilerplate/signature matching —
  `get_text()` inserts its separator at every tag boundary, so a
  phrase split across tags (e.g. a randomly bolded word in "Sent
  <strong>from</strong> my iPhone") comes out with doubled spaces that
  a naive single-space regex would silently fail to match.
- The cleaned subject + body are combined into one `text` string, then
  `chunk_text()` splits *that* into one or more chunks of at most 400
  characters, breaking on sentence boundaries (falling back to a
  word-boundary split only if a single sentence alone is too long).
  Consecutive chunks overlap by ~60 characters, so a point made right at
  a split isn't context-free on either side of it. Most tickets here are
  well under 400 characters and come out as a single chunk — chunking
  only does real work once a ticket runs long (a rambling multi-issue
  complaint, a long quoted thread). The `response` field isn't chunked;
  it's copied onto every chunk of its ticket as-is, since it's RAG
  context to hand the LLM, not something to search over.

Confirm the chunking actually did something — one of the generated
tickets is deliberately long to exercise it:
```bash
psql "postgresql://pipeline:pipeline@localhost:5433/support_tickets" \
     -c "SELECT ticket_id, COUNT(*) FROM ticket_chunks GROUP BY ticket_id HAVING COUNT(*) > 1;"
```

**Exercise for students:** add a new validation rule (e.g. reject
tickets with a category not in the known list) and confirm it shows up
in `tickets_rejected`.

## Day 2: Embedding -> Vector store -> Query

```bash
python src/pipeline.py --day 2   # builds embeddings + vector store from Day 1's output
python src/query.py "I was charged twice this month"
python src/query.py "cant log in, password reset broken" --top_k 3
python src/query.py "app crashes on export" --category bug
```

Or run interactively:
```bash
python src/query.py
```

`embed.py` embeds every chunk with `sentence-transformers/all-MiniLM-L6-v2`
(`src/embed.py::_get_model()` — cached per-process with `lru_cache` so a
query loop doesn't reload the model on every question) instead of fitting
a TF-IDF vectorizer. The first run downloads the model from the Hugging
Face Hub; every run after that loads it from the local cache and needs no
network access. Swapping in a different or larger open model — or a
hosted embeddings API — only means changing `MODEL_NAME`/`embed_query()`
in `embed.py` and `EMBED_DIM` in `db.py` if the new model's dimension
differs; `vector_store.py` and `query.py` don't change, they just expect
a fixed-size vector.

`vector_store.py` pushes both the similarity search and the category
filter into SQL:

```sql
SELECT ... , 1 - (e.embedding <=> %(qvec)s) AS score
FROM ticket_embeddings e JOIN ticket_chunks c USING (chunk_id)
WHERE c.category = %(category)s   -- only when --category is passed
ORDER BY e.embedding <=> %(qvec)s LIMIT %(top_k)s
```

`<=>` is pgvector's cosine-distance operator, matched against the HNSW
index from `db.py`'s schema — at ~300 rows a sequential scan would be
just as fast, but this is exactly the query shape and index a real
deployment needs once the corpus doesn't fit comfortably in memory.

**Exercise for students:** try queries that don't closely match the
canned templates (e.g. paraphrased or oddly worded) and compare the
results you get here to what a TF-IDF+SVD baseline would have returned
(swap `embed.py` back to fit a `TfidfVectorizer` for a quick before/after)
— good discussion point on lexical vs. semantic similarity.

## Full pipeline in one command

```bash
python src/pipeline.py
```

## Chatbot API (Stage 7: serving over HTTP)

A FastAPI backend in `api/` wraps the same retrieval used by `query.py`
and adds an LLM on top: retrieve the top-k most similar ticket chunks
from pgvector, then hand them to **Gemini Flash** (Google's free-tier
model) as context so it answers in plain language instead of returning
raw ticket text.

```
api/
├── main.py     # FastAPI app: POST /chat, GET /health
├── rag.py      # retrieval (reuses embed.py + vector_store.py) + Gemini call
└── schemas.py  # request/response models
```

Setup:
```bash
pip install -r requirements.txt
cp .env.example .env
# put a free key from https://aistudio.google.com/apikey into .env
```

Make sure Day 1 + Day 2 have already been run at least once (Postgres
needs `ticket_embeddings` populated — see above). Then start the API:
```bash
uvicorn api.main:app --reload --port 8000
```

Query it:
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "I was charged twice this month", "top_k": 5}'
```

Response shape:
```json
{
  "answer": "...",
  "sources": [
    {"ticket_id": "...", "category": "billing", "score": 0.87, "text": "..."}
  ]
}
```

`category` is optional in the request body and filters retrieval to one
of `billing`, `login`, `refund`, `bug`, `feature_request`, `shipping` —
same filter `vector_store.py` already pushes into SQL for `query.py
--category`. Interactive docs are at `http://localhost:8000/docs`.

**Exercise for students:** the retrieval store and Gemini model are each
cached as singletons (`@lru_cache`) so they're built once per process,
not per request — trace through `api/rag.py` and explain why that
matters for a server handling concurrent requests, vs. `query.py`'s CLI
where it doesn't.

## Stretch goals

- **Swap in a bigger or hosted embedding model:** try a larger open
  model (e.g. `all-mpnet-base-v2`) or a hosted embeddings API
  (OpenAI/Anthropic) in place of `all-MiniLM-L6-v2` — change
  `MODEL_NAME`/`embed_query()` in `embed.py` and `EMBED_DIM` in `db.py`
  to match the new dimension. `ticket_embeddings.embedding`'s column type
  is fixed at creation time, so you'll need to drop the table yourself
  before re-running `pipeline.py --day 2`:
  `psql "postgresql://pipeline:pipeline@localhost:5433/support_tickets" -c "DROP TABLE ticket_embeddings;"`
- **Add logging/error handling** to each stage script.
- **Build a simple UI:** wrap `query.py`'s `run_query()` in a
  Streamlit/Gradio app.
- **Schedule it:** wrap `pipeline.py` in a cron job or an Airflow DAG
  so it re-runs on new ticket data automatically.
