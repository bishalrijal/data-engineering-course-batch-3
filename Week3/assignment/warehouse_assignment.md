# Warehouse Assignment — Week 3, Part 2

With raw movie JSON landing in `data/raw/` from Part 1, design and build a star schema for it —
same fact/dimension shape as `ride_dw` from class, but this time you're drawing the model
yourself instead of following one.

Write your `CREATE TABLE` statements in [`warehouse_template.sql`](warehouse_template.sql), your
load script from [`extract_starter.py`](extract_starter.py)'s sibling pattern as `load.py`, and
your analytical queries in [`analysis_queries_template.sql`](analysis_queries_template.sql).

## Fields available per movie

Each raw JSON file has (among others): `Title`, `Year`, `Rated`, `Released`, `Runtime` (e.g.
`"148 min"`), `Genre` (e.g. `"Action, Sci-Fi, Thriller"`), `Director`, `Actors`, `Country`,
`Language`, `imdbRating`, `imdbVotes` (e.g. `"2,345,678"`), `imdbID`, `BoxOffice` (e.g.
`"$28,341,469"` or `"N/A"`), and `Ratings` — a list of `{"Source": ..., "Value": ...}` objects,
one of which may be `"Source": "Rotten Tomatoes"` with a value like `"87%"`.

Missing values come through as the **string** `"N/A"`, not `null` or an empty field — your load
script needs to catch that and convert it to a real `NULL`.

---

### Q1 — `dim_movie` (Basic · Dimension design)

One row per movie holding the descriptive, rarely-changing attributes: `movie_key` (surrogate
PK), `imdb_id` (natural key, `UNIQUE NOT NULL` — this is what your loader will `ON CONFLICT`
against to stay idempotent), `title`, `rated`, `plot`, `poster_url`.

---

### Q2 — `dim_director`, `dim_country`, `dim_language` (Basic · Dimension design)

Three small lookup dimensions: `director_key`/`name`, `country_key`/`country_name`,
`language_key`/`language_name` — each with a `UNIQUE` name column so your loader can
upsert without creating duplicates.

`Director`, `Country`, and `Language` can each list multiple values
(`"USA, UK"`). To keep scope reasonable, store only the **first-listed** value for these three —
note that simplification in a one-line comment above each table. (Genre gets the full
many-to-many treatment below — that's the one multi-valued field this assignment models
properly.)

---

### Q3 — `dim_genre` + `bridge_movie_genre` (Intermediate · Many-to-many modeling)

`Genre` is a genuine many-to-many relationship — a movie has several genres, a genre spans many
movies — and collapsing it into one dimension row (like Q2's simplification) would silently lose
data. Model it properly:

- `dim_genre`: `genre_key`, `genre_name` (`UNIQUE`)
- `bridge_movie_genre`: `movie_key`, `genre_key` — composite primary key on both columns, both
  `REFERENCES` their parent table

In a comment, explain why `dim_movie` can't just have a `genre_key` foreign key column the way it
has a `director_key` — what would break, or what would you lose, if you tried.

---

### Q4 — `dim_certificate` (Basic · Dimension design)

A small dimension for the `Rated` field (`PG-13`, `R`, `G`, `Not Rated`, etc.) —
`certificate_key`, `code` (`UNIQUE`). You'll link `fact_movie` to this instead of storing the
raw string on the fact table directly — same reasoning as `dim_payment_method` in `ride_dw`.

---

### Q5 — `dim_release_date` (Intermediate · Date dimension)

A calendar dimension for `Released`, built the same way `dim_date` was built in class:
`date_key` (`YYYYMMDD` integer PK), `full_date`, `year`, `decade` (e.g. `1990` for a 1994
release), `month`, `month_name`.

Populate it with `generate_series` the same way class did, covering `1900-01-01` through today —
movies span a much wider date range than the ride-sharing data did.

---

### Q6 — `fact_movie` (Intermediate · Fact table design)

One row per movie. Foreign keys to every dimension above (`movie_key`, `director_key`,
`country_key`, `language_key`, `certificate_key`, `release_date_key` — all `NOT NULL` except
wherever OMDb might genuinely have `N/A`), plus the numeric measures: `runtime_minutes`,
`imdb_rating`, `imdb_votes`, `metascore`, `rotten_tomatoes_pct` (parsed out of the `Ratings`
list), `box_office_usd`.

Add a `UNIQUE` constraint tying each fact row back to its `dim_movie` row (e.g. on `movie_key`) —
this is what makes `load.py` safe to re-run without doubling up rows, the same role
`source_trip_id` played on `fact_trips`.

---

### Q7 — `load.py` (Intermediate–Advanced · ETL)

Read every JSON file in `data/raw/` (skip the `search_*.json` files from Part 1 — those aren't
per-movie records) and load all of the above, in FK-dependency order. Specifically handle:

- `"N/A"` string → `NULL`, wherever it appears
- `Runtime`: `"148 min"` → integer `148`
- `imdbVotes`: `"2,345,678"` → integer `2345678`
- `BoxOffice`: `"$28,341,469"` → numeric `28341469`
- `Genre`: split on `", "` into one `bridge_movie_genre` row per genre
- `Ratings`: find the entry where `Source == "Rotten Tomatoes"` and parse `"87%"` → integer `87`
  (this source is often missing — handle that as `NULL`, not a crash)
- Upsert every dimension (`ON CONFLICT (name) DO NOTHING`, then look up the key) so re-running
  the loader against files it's already loaded doesn't create duplicate directors, genres,
  countries, etc.
- Wrap each movie's full load (dims + bridge rows + fact row) in one transaction, same principle
  as the daily-loader project — a crash partway through one movie shouldn't leave it half-loaded.

---

### Q8 — Best-rated movie per genre (Intermediate · Window functions)

For every genre, the single highest `imdb_rating` movie in that genre. Return `genre_name`,
`title`, `imdb_rating` — one row per genre. You'll need a window function over
`bridge_movie_genre` joined out to `dim_genre`, `dim_movie`, and `fact_movie`.

---

### Q9 — Average rating by decade (Basic–Intermediate · Aggregation)

Return `decade`, `movie_count`, and `avg_imdb_rating` (2 decimals), one row per decade
represented in your data, sorted chronologically. Uses `dim_release_date`.

---

### Q10 — Directors with the highest average box office (Intermediate · Aggregation + filtering)

Return `director_name`, `movies_loaded`, and `avg_box_office_usd` for every director who has
**2 or more** movies loaded, sorted by `avg_box_office_usd` descending. The `HAVING` clause
matters here — a director with a single blockbuster shouldn't outrank someone with a consistently
strong track record across several films.
