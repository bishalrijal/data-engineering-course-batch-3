-- Week 3 Warehouse Assignment — Analytical Queries
-- Run these against your loaded movie_dw. See warehouse_assignment.md for the full scenario text.


-- Q8 — Best-rated movie per genre (Intermediate · Window functions)
-- genre_name, title, imdb_rating — one row per genre, the single highest-rated movie in it



-- Q9 — Average rating by decade (Basic–Intermediate · Aggregation)
-- decade, movie_count, avg_imdb_rating (2 decimals) — one row per decade, sorted chronologically



-- Q10 — Directors with the highest average box office (Intermediate · Aggregation + filtering)
-- director_name, movies_loaded, avg_box_office_usd — only directors with 2+ movies loaded,
-- sorted by avg_box_office_usd descending
