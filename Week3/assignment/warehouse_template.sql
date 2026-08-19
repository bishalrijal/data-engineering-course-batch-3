-- Week 3 Warehouse Assignment — Answers
-- Fill in each CREATE TABLE below. See warehouse_assignment.md for the full spec.
-- Run this against a fresh database, e.g.:
--   psql -U postgres -d postgres -c "CREATE DATABASE movie_dw;"
--   psql -U postgres -d movie_dw -f warehouse.sql


-- Q1 — dim_movie
-- movie_key (surrogate PK), imdb_id (UNIQUE NOT NULL, natural key), title, rated, plot, poster_url



-- Q2 — dim_director, dim_country, dim_language
-- Each: surrogate key + UNIQUE name column. Store only the first-listed value from the
-- comma-separated OMDb field — note the simplification in a comment on each table.



-- Q3 — dim_genre + bridge_movie_genre
-- dim_genre: genre_key, genre_name (UNIQUE)
-- bridge_movie_genre: movie_key, genre_key — composite PK, both REFERENCES
-- Comment: why can't dim_movie just have a genre_key FK column like it has director_key?



-- Q4 — dim_certificate
-- certificate_key, code (UNIQUE) — for the Rated field (PG-13, R, G, Not Rated, ...)



-- Q5 — dim_release_date
-- date_key (YYYYMMDD INTEGER PK), full_date, year, decade, month, month_name
-- Populate with generate_series, 1900-01-01 through today (same pattern as class's dim_date)



-- Q6 — fact_movie
-- One row per movie. FKs to every dimension above, plus measures:
-- runtime_minutes, imdb_rating, imdb_votes, metascore, rotten_tomatoes_pct, box_office_usd
-- UNIQUE constraint tying each row back to its dim_movie row (for idempotent loads)
