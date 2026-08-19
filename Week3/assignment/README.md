# Week 3 Assignment — IMDb Movie Data Warehouse

Two parts, same end-to-end shape as the ride-sharing ETL you built in class, but this time
**you're the one designing the warehouse** and the source is a live HTTP API instead of another
Postgres database:

1. **[Extraction](extraction_assignment.md)** — pull movie data from the OMDb API (a REST API that
   serves IMDb's data) into a raw JSON staging layer.
2. **[Warehouse design](warehouse_assignment.md)** — design and build a star schema (fact +
   dimension + bridge tables) for movie analytics, load it from your raw JSON, and write a few
   analytical queries against the finished thing.

Part 2 depends on Part 1's output, so do them in order.

## Why OMDb

IMDb itself has no public API. [OMDb](https://www.omdbapi.com/) is a free, well-known REST API
that wraps IMDb's data (ratings, cast, genres, box office, etc.) as JSON — close enough to "the
IMDb API" for this exercise, and a realistic stand-in for the kind of third-party API you'll
integrate with on the job.

## Setup

1. Get a free API key: [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx) → "Free"
   tier (1,000 requests/day) → enter your email → the key arrives by email within a few minutes.
   Activate it by clicking the link in that email before using it.
2. Same virtual environment as the rest of Week 3 — if you haven't already:
   ```bash
   python3 -m venv Week3/.venv
   source Week3/.venv/bin/activate      # Windows: Week3\.venv\Scripts\activate
   pip install -r Week3/requirements.txt
   ```
3. Add your key to `Week3/.env` (same file the rest of Week 3 reads via `python-dotenv`):
   ```
   OMDB_API_KEY=your_key_here
   ```
   Never commit this file — it's already gitignored.

## What to submit

All in this `Week3/assignment/` folder:

- `extract.py` — your extraction script, filled in from [`extract_starter.py`](extract_starter.py)
- `warehouse.sql` — your `CREATE TABLE` statements for the full star schema, filled in from
  [`warehouse_template.sql`](warehouse_template.sql)
- `load.py` — the script that parses your raw JSON and loads it into the warehouse
- `analysis_queries.sql` — your answers to the 3 analytical questions in Part 2, filled in from
  [`analysis_queries_template.sql`](analysis_queries_template.sql)

Do **not** commit your `data/raw/` JSON files or your `.env` — both should stay local (add
`Week3/assignment/data/` to your `.gitignore` if it isn't already ignored).

## How to submit

```bash
git checkout main
git pull upstream main
git checkout -b week3-assignment

# ... complete extract.py, warehouse.sql, load.py, analysis_queries.sql ...

git add Week3/assignment/extract.py Week3/assignment/warehouse.sql \
        Week3/assignment/load.py Week3/assignment/analysis_queries.sql
git commit -m "Complete week 3 IMDb data warehouse assignment"
git push -u origin week3-assignment
```

Then open a pull request **on your own fork** — base: `main`, compare: `week3-assignment` — and
share the link with your instructor.
