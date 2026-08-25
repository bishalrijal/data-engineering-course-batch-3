# ride_etl

A dbt project that transforms the raw `ride_prod` OLTP copy (landed in `ride_dw.raw` by
`Week3/pipeline.py`) into a star schema, in two layers: `staging` (light cleanup) and `marts`
(the actual dimensional model).

For how to install, configure, and run this project, see
**[`Week3/dbt-setup.md`](../../Week3/dbt-setup.md)**. This file explains what each folder is
for.

## Data flow

```
ride_prod (OLTP)
    │  Week3/pipeline.py — 1:1 copy, no transformation
    ▼
ride_dw.raw            (declared in models/staging/_sources.yml)
    │  models/staging/*.sql — rename/cast, one view per raw table
    ▼
ride_dw.staging
    │  models/marts/*.sql — join, dedupe, surrogate keys, business logic
    ▼
ride_dw.marts           (dim_driver, dim_passenger, dim_location,
                          dim_payment_method, dim_promo_code, fact_trips)
```

## Project structure

### `models/staging/`

One view per raw table (`stg_drivers`, `stg_trips`, …), each a thin `select` off
`{{ source('raw', '<table>') }}` — renaming, casting, and the occasional derived column
(e.g. `stg_trips` computes `date_key`), but no joins and no business logic. Materialized as
**views** (`+materialized: view` in `dbt_project.yml`) since they're cheap to recompute and
mostly exist to give the marts layer a stable, typed interface instead of querying `raw`
directly.

`_sources.yml` declares the `raw` schema as a dbt **source** (so `{{ source(...) }}` can
reference it) and carries schema tests against the raw tables themselves — catching a landing
problem in `pipeline.py` before it ever reaches a model. `_staging.yml` carries the equivalent
tests one layer up, against the staging views.

### `models/marts/`

The business-facing star schema: five dimension tables (`dim_driver`, `dim_passenger`,
`dim_location`, `dim_payment_method`, `dim_promo_code`) and one fact table (`fact_trips`).
This is where surrogate keys are generated (`row_number() over (...)`), dimensions are joined
into the fact, and sentinel rows are added (e.g. `dim_payment_method`'s "Unknown" row for trips
with no payment method). Materialized as **tables** (`+materialized: table`) since downstream
queries and BI tools should hit a precomputed table, not re-run the joins every time.

`_marts.yml` carries the schema tests — `unique`/`not_null` on every key, `accepted_values` on
every status/category column, and `relationships` tests wiring `fact_trips`' foreign keys back
to each dimension.

Both `staging` and `marts` land in their own Postgres **schemas** (`+schema:` in
`dbt_project.yml`, combined with the `generate_schema_name` macro below) — never in `public`,
which `Week3/warehouse.sql` / `Week3/etl.py` own.

### `macros/`

Reusable Jinja. Currently just `generate_schema_name.sql`, which overrides dbt's default
schema-naming behavior. Without it, a model configured with `+schema: marts` would build into
`<profile_target_schema>_marts` (dbt's out-of-the-box convention is to prefix custom schemas
with the target schema); this macro makes it build into a clean `marts` instead. This is also
the mechanism that keeps dbt from ever writing into `public`.

### `tests/`

**Singular tests** — one `.sql` file per test, each a `select` that should return zero rows;
any row it does return is a failure. Used for checks that don't fit the generic
column-level tests in a `_*.yml` file, typically because they involve a business rule or a
comparison between columns rather than a single column's values (e.g.
`assert_fact_trips_discount_not_exceeding_base_fare.sql` checks `discount_amount <= base_fare`
across the whole table). Contrast with the **generic/schema tests** declared under `data_tests:`
in `_sources.yml`, `_staging.yml`, and `_marts.yml` (`unique`, `not_null`, `accepted_values`,
`relationships`) — those are reusable and parameterized per column; singular tests are one-off
SQL for a rule specific to one model.

### `seeds/`

Where version-controlled CSV reference data would live (e.g. a static region-to-state mapping),
loaded into the warehouse via `dbt seed`. Currently empty — this project derives `dim_location`'s
`region` with a `case` expression in SQL instead, since the mapping is small. Reach for a seed
if that list grows large enough that maintaining it as SQL becomes awkward.

### `snapshots/`

Where Type-2 slowly-changing-dimension tracking would live, via `dbt snapshot` — capturing a
row's value *and* the time range it was valid for, so you can ask "what was this driver's status
on March 3rd?" instead of only ever seeing the current value. Currently empty: `dim_driver` and
`dim_passenger` overwrite on every `dbt build` (Type-1 style, current-value-only), since raw is a
full truncate-and-reload rather than a change-tracked source. Add a snapshot here if that ever
needs to change.

### `analyses/`

Ad hoc `.sql` files that are compiled by `dbt compile` (so they can use `ref()`/`source()`/Jinja
like a real model) but never run or materialized — for one-off exploratory queries you want
under version control without them becoming part of the build. Currently empty.

### `target/` and `logs/`

Both fully auto-generated and gitignored — don't hand-edit anything here.

- `target/` — build artifacts: compiled SQL (`target/compiled/`), the executed SQL from the last
  run (`target/run/`), and metadata (`manifest.json`, `run_results.json`, `catalog.json`) that
  `dbt docs` and other tooling read. Wiped by `dbt clean`.
- `logs/` — dbt's own run logs (`dbt.log`).

### Top-level files

- **`dbt_project.yml`** — the project's config: where models/tests/seeds/etc. live, and the
  per-directory materialization + schema defaults described above.
- **`profiles.yml`** — the Postgres connection (host/user/password/dbname). Gitignored since it
  holds a plaintext password; see `Week3/dbt-setup.md` for the template to recreate it locally.
- **`.user.yml`** — dbt-generated local user metadata (an anonymous ID for the CLI's usage
  stats). Not project config; safe to ignore.
