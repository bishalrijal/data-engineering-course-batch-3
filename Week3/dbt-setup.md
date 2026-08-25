# dbt Setup & Usage — Ride-Sharing Warehouse

This covers the **dbt half** of the Week 3 ride-sharing warehouse: taking a raw, 1:1 copy of
the `ride_prod` OLTP tables and transforming it into a star schema, entirely through SQL
models instead of hand-written Python ETL.

It's a second, parallel path to the same warehouse database (`ride_dw`) that
`Week3/etl.py` / `Week3/warehouse.sql` already build — see [How this fits together](#how-this-fits-together)
below for how the two stay out of each other's way.

## Prerequisites

- `ride_prod` populated — follow the **Prerequisites** and **Step 1/2** sections of
  [`Week3/README.md`](README.md) first if you haven't already.
- The `ride_dw` database must exist (it does **not** need `Week3/warehouse.sql` to have been
  run — dbt builds its own schemas independently of the `public` schema that script owns):
  ```bash
  psql -U postgres -d postgres -c "CREATE DATABASE ride_dw;"
  ```
  Skip this if you already created `ride_dw` for the `etl.py` workflow.
- Python 3 with `Week3/requirements.txt` installed (same venv as the rest of Week 3 — see the
  main README's Prerequisites section). This is what runs `pipeline.py`.
- dbt itself, in its **own** virtual environment (keep it separate from the Week 3 Python venv —
  dbt pulls in a large, unrelated dependency tree):
  ```bash
  python3 -m venv dbt/.venv
  source dbt/.venv/bin/activate        # Windows: dbt\.venv\Scripts\activate
  pip install dbt-core dbt-postgres
  ```
  `dbt/.venv/` is already covered by the repo's `.gitignore`. Keep it activated for every `dbt`
  command below.

## Step 1 — land the raw data

dbt never reads `ride_prod` directly — `Week3/pipeline.py` copies each OLTP table 1:1 into a
`raw` schema inside `ride_dw` first (no transformation, just a landing zone). It reads its
connection settings from `Week3/.env` (via `python-dotenv`):

| Variable | Default | Purpose |
|---|---|---|
| `SRC_DB_HOST` / `SRC_DB_PORT` / `SRC_DB_NAME` / `SRC_DB_USER` / `SRC_DB_PASSWORD` | `localhost` / `5432` / `ride_prod` / `postgres` / `postgres` | source (OLTP) |
| `DST_DB_HOST` / `DST_DB_PORT` / `DST_DB_NAME` / `DST_DB_USER` / `DST_DB_PASSWORD` | `localhost` / `5432` / `ride_dw` / `postgres` / `postgres` | destination (warehouse) |

If your local setup matches the defaults, no `.env` is needed. Otherwise create
`Week3/.env` (already gitignored) with whichever of the above you need to override.

Run it from the repo root, with the Week 3 venv activated:

```bash
python3 Week3/pipeline.py
```

Expected output:

```
drivers: 25 rows loaded into raw.drivers
passengers: 45 rows loaded into raw.passengers
locations: 25 rows loaded into raw.locations
payment_methods: 7 rows loaded into raw.payment_methods
promo_codes: 10 rows loaded into raw.promo_codes
trips: 10000 rows loaded into raw.trips
trip_cancellations: 1531 rows loaded into raw.trip_cancellations
```

It's a full truncate-and-reload every time — safe to re-run whenever `ride_prod` changes.

## Step 2 — configure the dbt connection

The project's connection profile is `dbt/ride_etl/profiles.yml`. It's **gitignored** (it holds a
plaintext password) and won't exist yet on a fresh clone — create it yourself:

```yaml
# dbt/ride_etl/profiles.yml
ride_etl:
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      dbname: ride_dw
      user: postgres
      pass: <your postgres password>
      schema: public   # fallback only — every model sets its own schema explicitly
      threads: 1
  target: dev
```

The profile name (`ride_etl`) must match the `profile:` value in `dbt/ride_etl/dbt_project.yml`
— it already does, don't change it.

Because `profiles.yml` lives inside the project directory instead of dbt's default
`~/.dbt/profiles.yml`, every command below passes `--profiles-dir .`.

## Step 3 — run it

All commands run from `dbt/ride_etl/`, with the dbt venv activated:

```bash
cd dbt/ride_etl

# sanity-check the connection and profile
dbt debug --profiles-dir .

# build every model (staging views + mart tables) AND run every test, in dependency order
dbt build --profiles-dir .
```

`dbt build` is the one command you need day to day — it runs models and tests together, in the
correct order, and stops a downstream model from building on top of data that just failed a test
upstream. If you want them separately:

```bash
dbt run --profiles-dir .    # models only
dbt test --profiles-dir .   # tests only (against whatever was last built)
```

Expected tail of `dbt build`:

```
Finished running 6 table models, 147 data tests, 6 view models in ...
Done. PASS=159 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=159
```

## Verifying it worked

```sql
-- schemas dbt owns, sitting alongside (not inside) public
select schemaname, tablename from pg_tables
where schemaname in ('raw', 'staging', 'marts')
order by 1, 2;

select * from marts.fact_trips limit 5;
```

## Viewing the documentation site

dbt can generate a browsable documentation website — model/column descriptions, which tests
are attached to each column, and an interactive lineage (DAG) graph showing how `raw` flows
through `staging` into `marts`.

```bash
dbt docs generate --profiles-dir .   # builds target/catalog.json from the live database schema
dbt docs serve --profiles-dir .      # serves the site at http://localhost:8080
```

`dbt docs serve` blocks the terminal — leave it running and open
[http://localhost:8080](http://localhost:8080) in a browser; `Ctrl+C` stops it. Use `--port` to
pick a different port if 8080 is taken (`dbt docs serve --profiles-dir . --port 8081`).

Once it's open:

- Click the **compass icon** (bottom right) for the full lineage graph, or the small graph icon
  on any model's detail page for just that model's upstream/downstream.
- Click a model (e.g. `fact_trips`) in the left-hand tree to see its columns, descriptions, and
  the list of tests declared on each one.
- The **Sources** section lists `raw`'s tables and the tests declared in `_sources.yml`.

Re-run `dbt docs generate` after changing any model, column, or test so the site reflects the
current project — `dbt docs serve` doesn't pick up changes on its own.

**What this site does *not* show: pass/fail test results.** It's built purely from
`manifest.json` (project structure) and `catalog.json` (live column stats) — it lists which
tests exist on a column, not whether they last passed. See the next section for where actual
results live.

## Viewing test results

`dbt build` / `dbt test` print each test's result to the terminal as it runs:

```
83 of 159 START test not_null_stg_trips_pickup_location_id ..................... [RUN]
83 of 159 PASS not_null_stg_trips_pickup_location_id ........................... [PASS in 0.04s]
...
Done. PASS=159 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=159
```

That's the real-time source of truth. Every command also writes the same information as
structured JSON to `target/run_results.json` (one entry per node, with `status` and
`execution_time`) — useful if you want to inspect results after the fact without re-scrolling
the terminal. Note that this file always reflects the **most recently run command**, so run
`dbt test` or `dbt build` (not `dbt docs generate`, which overwrites it with compile-only
statuses) right before reading it:

```bash
python3 -c "
import json
results = json.load(open('target/run_results.json'))['results']
tests = [r for r in results if r['unique_id'].startswith('test.')]
failed = [r for r in tests if r['status'] != 'pass']
print(f\"{len(tests) - len(failed)}/{len(tests)} tests passed\")
for r in failed:
    print(' -', r['status'].upper(), r['unique_id'])
"
```

There's no bundled graphical pass/fail dashboard in open-source dbt — that's a dbt Cloud
feature, or something you'd get from an add-on package like `elementary-data`. For this
project, the terminal output + `run_results.json` above is the full picture.

## Other useful commands

| Command | What it does |
|---|---|
| `dbt compile --profiles-dir .` | Renders Jinja/`ref()`/`source()` into plain SQL under `target/compiled/`, without running anything — good for debugging a model. |
| `dbt run --select stg_trips+ --profiles-dir .` | Build one model and everything downstream of it (`+` = "and descendants"). |
| `dbt test --select fact_trips --profiles-dir .` | Run only the tests attached to one model. |
| `dbt docs generate --profiles-dir . && dbt docs serve` | Generate and browse the auto-built data-lineage / column docs site. |
| `dbt clean` | Delete `target/` and `dbt_packages/` (build artifacts only — never touches the database). |

## Re-running end to end

Neither side is incremental, so the safe order after any source data change is:

```bash
python3 Week3/pipeline.py                      # refresh raw
cd dbt/ride_etl && dbt build --profiles-dir .   # rebuild staging + marts on top of it
```

## How this fits together

`ride_dw` ends up with two independent builds of (mostly) the same star schema, in different
schemas, from two different tools:

| Schema | Built by | How |
|---|---|---|
| `public` | `Week3/warehouse.sql` + `Week3/etl.py` | hand-written DDL + a Python extract/transform/load script |
| `raw` | `Week3/pipeline.py` | 1:1 copy of the OLTP tables, no transformation |
| `staging`, `marts` | dbt (`dbt/ride_etl/`) | SQL models reading from `raw`, transforming in views (`staging`) and tables (`marts`) |

They're isolated on purpose (see `dbt/ride_etl/dbt_project.yml`'s `+schema:` configs and the
`generate_schema_name` macro) specifically so that running `dbt build` can never drop or
overwrite the tables `etl.py` populated in `public` — both workflows can be run, re-run, and
compared side by side without stepping on each other.
