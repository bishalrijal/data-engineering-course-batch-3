# Week 3 — Sample Data

`ride_prod_sample.sql` and `sample_data_loader.py` together set up a more realistic,
production-shaped version of the ride-sharing schema from Week 2 — normalized to 3NF, with
driver licenses, vehicle fleet/assignment history, promo codes, dual ratings, and cancellation
detail split into their own tables, plus two views (`v_trips`, `v_promo_usage`) that restore the
computed columns (`fare_amount`, `duration_minutes`, `times_used`) a fully normalized schema
doesn't store directly.

New to virtual environments, or to `psycopg2`'s connection/cursor model? Read these first:

- [Virtual Environments — Pre-read](week3_venv_preread.html)
- [DB Connections with psycopg2 — Pre-read](week3_psycopg2_preread.html)

## Prerequisites

- PostgreSQL running locally, with a role that can `CREATE DATABASE` (the default `postgres`
  role can)
- Python 3, with the loader's dependencies (listed in `Week3/requirements.txt`) installed in a
  **virtual environment** so they don't leak into your global Python install. Run this once from
  the repo root (same place every command below runs from):
  ```bash
  python3 -m venv Week3/.venv
  source Week3/.venv/bin/activate      # Windows: Week3\.venv\Scripts\activate
  pip install -r Week3/requirements.txt
  ```
  `Week3/.venv/` is already covered by the repo's `.gitignore`. Keep this environment activated
  for every `python3` command below — if you open a new terminal, re-run the `source` line first
  (`deactivate` exits it when you're done).

## Step 1 — create the database and schema

`ride_prod_sample.sql` starts with `CREATE DATABASE ride_prod;`, so it needs to run in two
parts — you can't create a database and then use it in the same connection. This trips people up
in DBeaver specifically, because a SQL Editor tab stays pinned to whichever database it was
opened against.

### In DBeaver

1. Open a **SQL Editor** on your existing PostgreSQL connection (whatever database it currently
   points at, e.g. `postgres` — it doesn't matter, you're only creating a new database from
   here). Run just this one line:
   ```sql
   CREATE DATABASE ride_prod;
   ```
2. In the **Database Navigator**, right-click your connection and choose **Refresh** (or press
   `F5`) so `ride_prod` shows up in the list of databases.
3. Open a **new** SQL Editor, this time scoped to `ride_prod` — either select `ride_prod` in the
   Database Navigator first and then open the SQL Editor from there, or use the database
   selector dropdown in the SQL Editor's toolbar to switch it from `postgres` to `ride_prod`.
   Double-check the toolbar shows `ride_prod` before continuing — running the schema against the
   wrong database is the single most common mistake here.
4. Open `Week3/ride_prod_sample.sql` in that editor (**File → Open File…**). Since you already
   created the database in step 1, its first line will now fail if you run it again
   (`database "ride_prod" already exists`) — select everything **starting from the `DROP VIEW`
   line** (i.e. skip just that first `CREATE DATABASE` line) and run it with **Execute SQL
   Script** (not "Execute SQL Statement" — you want the whole selection run as a script, not
   just the one statement under your cursor). Every `CREATE TABLE`, `CREATE INDEX`, and
   `CREATE VIEW` after it should succeed.

### On the command line

```bash
# 1. Create the database (connect to any existing db to run this, e.g. postgres)
psql -U postgres -d postgres -c "CREATE DATABASE ride_prod;"

# 2. Connect to the new database and build the schema
psql -U postgres -d ride_prod -f Week3/ride_prod_sample.sql
```

The second command will print one harmless error on its very first line —
`database "ride_prod" already exists` — because the script's own `CREATE DATABASE` statement
runs again against a database that (2 seconds ago) you just created. That's expected; `psql`
prints the error and keeps going, unlike DBeaver's script runner. Every `CREATE TABLE`,
`CREATE INDEX`, and `CREATE VIEW` statement after it should succeed.

Re-running this script at any point drops and recreates every table (`DROP ... IF EXISTS` at
the top), so it's always safe to use as a full reset — in DBeaver, skip that first line again
the same way.

## Step 2 — load sample data

The loader reads its connection settings from environment variables (via `python-dotenv`), with
these defaults if unset:

| Variable | Default |
|---|---|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `ride_prod` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `postgres` |

If your local setup matches the defaults, no configuration is needed. Otherwise, create a
`.env` file in the repo root (already gitignored) with whichever of the above you need to
override, e.g.:

```
DB_PASSWORD=mysecretpassword
```

Then run the loader:

```bash
python3 Week3/sample_data_loader.py
```

It generates and inserts, in FK-dependency order:

| Table | Rows |
|---|---|
| `locations` | 25 |
| `payment_methods` | 7 |
| `promo_codes` | 10 |
| `drivers` (+ 1 license each) | 25 |
| `vehicles` (+ assignments) | 30 |
| `passengers` | 45 |
| `trips` | 10,000 (≈80% completed · 15% cancelled · 5% no_show) |
| `trip_cancellations` | ~1,500 (one per cancelled trip) |

The whole run takes a couple of seconds and prints a final row-count summary. The data is
generated with a fixed seed (`SEED = 42`), so every run produces the same values.

## Re-running the loader

The loader is **not** idempotent — running it a second time against an already-populated
database fails immediately on a duplicate `locations` row (the same seed regenerates the same
city rows) and rolls back cleanly before touching `trips`, so nothing gets corrupted, but nothing
gets added either. To load fresh data, reset the schema first.

On the command line:
```bash
psql -U postgres -d postgres -c "DROP DATABASE ride_prod;"
psql -U postgres -d postgres -c "CREATE DATABASE ride_prod;"
psql -U postgres -d ride_prod -f Week3/ride_prod_sample.sql
python3 Week3/sample_data_loader.py
```

In DBeaver: Postgres won't let you `DROP DATABASE ride_prod` from a SQL Editor that's currently
connected *to* `ride_prod` (you can't drop the database you're sitting in). Either switch that
editor's database selector back to `postgres` first and run `DROP DATABASE ride_prod;` there, or
right-click `ride_prod` in the Database Navigator and choose **Delete/Drop**. Then repeat
Step 1 and re-run the loader.

## Verifying it worked

Run these in a SQL Editor connected to `ride_prod` (in DBeaver or `psql`, doesn't matter):

```sql
-- fare_amount and duration_minutes are computed in the view, not stored on trips
SELECT trip_id, fare_amount, duration_minutes, status FROM v_trips LIMIT 5;

-- times_used is always fresh, never a stale stored counter
SELECT code, times_used FROM v_promo_usage ORDER BY times_used DESC LIMIT 5;
```
