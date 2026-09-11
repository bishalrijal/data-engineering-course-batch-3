# Future improvements

Things worth building next, roughly in order of leverage. None of this is
required for the pipeline to work as a teaching tool today — it's a
punch list for whoever picks this up next.

## Quick fix

- **`ingest.py` no longer calls `db.init_db()`** (removed in a recent edit),
  but `validate.py`, `clean_transform.py`, and `embed.py` still do. That
  breaks the "any stage is independently runnable on a fresh database"
  property the rest of the pipeline relies on — `python src/ingest.py`
  alone now fails on an empty database unless `python src/db.py` (or
  another stage) has run first. Either restore the call for consistency,
  or make the removal explicit and update the README/teaching material to
  match (it currently documents `python src/db.py` as a required first
  step, which is a reasonable design — just needs to be a deliberate,
  documented choice, not an inconsistency between the four stage scripts).

## Testing

Zero automated coverage today. This project has already taken a lot of
iterative edits (PII redaction, chunking, the `dict_row` refactor, the
SQL/migrations split) with nothing catching a regression except manually
rerunning the pipeline end to end each time.

- Unit tests for the pure functions: `redact_pii`, `strip_html`,
  `strip_signature`, `chunk_text` — especially edge cases (empty text,
  exactly-at-400-chars, a sentence with no punctuation at all, PII split
  across an HTML tag boundary).
- One integration test that runs the full pipeline against a disposable
  test database (a second `docker compose` service, or `testcontainers`)
  and asserts row/rejection counts match expectations — the same numbers
  the README currently asks students to eyeball (4 rejected, 1 PII match,
  etc.) as actual assertions.

## Retrieval quality

Two gaps observed live while testing `/chat`:

- **No similarity threshold.** `/chat` always returns `top_k` results even
  for a wildly unrelated query, forcing weak matches into the LLM's
  context instead of the model being told "nothing relevant was found."
  Add a minimum cosine-similarity cutoff in `vector_store.py::search()`.
- **No de-duplication across chunks of the same ticket.** A query can
  surface multiple chunks from one long ticket (we saw this happen with
  the multi-chunk billing ticket) and none from otherwise-relevant
  tickets. Cap chunks-per-`ticket_id` in the retrieved set, or re-rank for
  diversity, so the context budget isn't spent on redundant text from a
  single source.

## RAG hardening

- **Prompt injection.** Ticket body/response text is untrusted (it's
  customer-submitted) and goes straight into the LLM prompt unescaped in
  `api/rag.py::_build_prompt()`. Worth clearly delimiting retrieved
  content from the instruction portion of the prompt, and testing what
  happens if a ticket body contains something like "ignore the above and
  say X."
- **No auth, wide-open CORS.** `api/main.py` has `allow_origins=["*"]` and
  no authentication on `/chat` — fine for a local classroom demo, not
  fine past that. Add an API key header check and restrict CORS to a
  known frontend origin before this touches real traffic.
- **Multi-turn conversation.** `/chat` is stateless/single-turn today. A
  real support chatbot needs to handle a follow-up ("how long will that
  take?") that only makes sense with the prior exchange as context.

## Prompt evaluation

There's no way today to know whether a change to `PROMPT_TEMPLATE` in
`api/rag.py` (we've already changed it once, to require restating the
resolution instead of just acknowledging the question) made answers
better or worse — every check so far has been one manual `curl` call and
eyeballing the response. That doesn't scale past the first prompt
iteration.

The data to build a real eval set already exists: every ticket has a
paired (question, resolution) — `response` on `ticket_chunks` — which is
effectively hand-labeled ground truth for "what should `/chat` say here."

1. **Retrieval eval.** For a sample of tickets, query with the ticket's
   own question (or a paraphrase of it) and check whether that ticket's
   `chunk_id`/`ticket_id` actually shows up in the `top_k` results —
   recall@k. Cheap to compute, and it isolates retrieval failures from
   generation failures (a wrong answer could be a bad match *or* a bad
   summary of a good match — this tells you which one it was).
2. **Generation eval.** Compare `/chat`'s actual `answer` against the
   ticket's `response` (the gold resolution). Two options, cheapest
   first:
   - Embedding similarity: reuse `embed_query()` (already in the
     codebase) to embed both the generated answer and the gold
     resolution, cosine-compare them — no new dependency, same model
     already loaded.
   - LLM-as-judge: ask Gemini a separate, structured prompt — "does this
     answer correctly convey this resolution: yes / partially / no" —
     more expensive per eval run, but catches cases embedding similarity
     misses (a fluent answer that's subtly wrong).
3. **Guardrail eval, specifically.** A held-out set of intentionally
   out-of-scope questions (no matching ticket exists) — assert the model
   says it doesn't have enough information rather than hallucinating a
   plausible-sounding answer. This is the one behavior most worth locking
   down with a real test, since a hallucinated support answer is the
   worst failure mode this system has.
4. **Wire it up as a regression gate**, not just an ad hoc script — run
   the eval set before/after any change to `PROMPT_TEMPLATE`, `top_k`
   defaults, or the embedding model, and diff the scores. Doesn't need a
   framework to start (a script over the existing `answer_query()`
   function is enough); `ragas` or `promptfoo` are worth a look once the
   homegrown version outgrows itself.
5. **Exercise for students:** deliberately regress the prompt (e.g.
   remove the "restate the resolution" instruction that's in there today)
   and watch the generation-eval score drop — a concrete way to see that
   prompt wording isn't cosmetic, it's measurably load-bearing.

## Chunking correctness

`chunk_text()` in `clean_transform.py` splits on *character* count
(400 chars, 60-char overlap), but `sentence-transformers/all-MiniLM-L6-v2`
has a 256-*token* limit. Character count and token count aren't the same
thing — a chunk dense with short words/punctuation could still overflow
the model's real limit. Token-aware chunking (splitting against the
model's actual tokenizer, e.g. via `AutoTokenizer` from `transformers`)
would be more correct than the current character-count heuristic.

## Observability

None of the stage scripts have real logging — a malformed CSV row or a
dropped Postgres connection currently just stack-traces raw. Add
structured logging plus basic per-stage metrics (row counts in/out,
rejection counts, elapsed time) to `ingest.py`, `validate.py`,
`clean_transform.py`, and `embed.py`. Useful both for realism and for
actually debugging pipeline runs in class instead of re-reading a raw
Python traceback with the students.

## Incremental ingestion & run planning

Today `ingest.py` does a full `TRUNCATE tickets_raw` + reload from
`data/raw/tickets_raw.csv` on every run, and `generate_data.py`
regenerates the *entire* synthetic dataset from scratch each time —
there's no notion of "new tickets since last run." That's fine for a
teaching pipeline, but the rest of the design (upserts everywhere
downstream, chunk-level re-processing) implies an incremental path that's
never actually been exercised.

Mirror the watermark pattern already taught in
`Week5/pipeline/extract.py::get_watermark()` and
`Week5/dags/ride_db_dw.py`'s `full_reload` `Param`:

1. Give tickets a real timestamp to watermark on — the synthetic
   `created_at` field exists already; it just needs to be a real
   timestamp rather than a bare date string, plus an `ingested_at` on the
   landing table (already present in `tickets_raw`).
2. Add `ingest.py::get_watermark(conn)`:
   ```sql
   SELECT COALESCE(MAX(ingested_at), '2000-01-01'::TIMESTAMPTZ) FROM tickets_raw
   ```
   — same fallback-to-full-load-on-empty-table pattern as Week5, so the
   first run behaves correctly with no special-casing.
3. Change `generate_data.py` to support *appending* a small batch of new
   tickets to the existing source instead of always overwriting the whole
   dataset — otherwise there's nothing for an incremental run to pick up.
4. Switch `ingest.py` from `TRUNCATE` + reload to inserting only rows
   newer than the watermark, with a `--full-reload` CLI flag as the
   escape hatch — same shape as the DAG's `full_reload` param below.
5. **Exercise for students:** run the pipeline once, append 5 new
   synthetic tickets, rerun, and confirm only those 5 flow through
   validate → clean → embed instead of all ~275 being reprocessed.

## Orchestrate with Airflow

This project runs today as manual `python src/*.py` calls via
`pipeline.py`. Week5 already taught Airflow's TaskFlow API on a similar
extract → transform → load shape (`Week5/dags/ride_db_dw.py`) — porting
that same pattern here is a natural next step, and a good exercise
linking Week5 and this project together.

1. A `dags/support_ticket_pipeline.py` DAG, `@task`-decorated, one task
   per existing stage function (`ingest.ingest`, `validate.validate`,
   `clean_transform.transform`, `embed.build_and_save`), wired
   `ingest >> validate >> clean_transform >> embed`. Each task is a thin
   wrapper calling the stage module's existing function — no pipeline
   logic duplicated in the DAG itself, same shallow-wrapper style as
   `ride_db_dw.py`'s tasks.
2. A `full_reload` boolean `Param` on the DAG, threaded through to
   `ingest`'s incremental/full-reload switch from the section above —
   mirrors `ride_db_dw.py`'s exact `full_reload` param, right down to the
   name.
3. Use `PostgresHook` with a configured `support_tickets_db` Airflow
   connection instead of `db.get_conn()`'s raw env vars, so credentials
   live in Airflow's connection store rather than `.env` when this runs
   orchestrated — a good discussion point on the difference between
   local-dev and orchestrated credential handling.
4. Match `ride_db_dw.py`'s defaults: `default_args={"retries": 2,
   "retry_delay": timedelta(minutes=5)}`, `schedule="@daily"`,
   `catchup=False` — a support-ticket sync into a searchable index should
   run on its own and retry transient DB hiccups, not need someone to
   remember to run it.
5. Once ingestion is incremental, Stage 4 (embedding) only needs to
   process the chunks that actually changed — `embed.py` already
   upserts on `chunk_id`, so this is really about the DAG feeding it a
   changed subset instead of always reading all of `ticket_chunks`, not
   a change to `embed.py` itself.
6. **Exercise for students:** trigger the DAG manually in the Airflow UI
   with `full_reload=true` vs `false`, compare task duration in the
   Gantt view, and explain why the incremental run's `clean_transform`
   and `embed` tasks finish faster.
