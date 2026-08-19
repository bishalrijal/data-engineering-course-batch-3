# Extraction Assignment — Week 3, Part 1

The analytics team at a small streaming startup wants a movie data warehouse, but there's no
source database to replicate this time — the data lives out on the internet, behind the OMDb API.
Your job is the **extract** step: pull raw movie data down and land it as JSON files before
anyone tries to model or query it.

Start from [`extract_starter.py`](extract_starter.py), which has the logging setup and `.env`
loading already wired up, matching the pattern from `Week3/etl.py`.

## The title list

Fetch full details for these 25 movies (title + year — pass both to OMDb so `The Matrix` doesn't
collide with a same-named film from another year):

```python
MOVIES = [
    ("Inception", 2010), ("The Dark Knight", 2008), ("Parasite", 2019),
    ("Spirited Away", 2001), ("The Godfather", 1972), ("Pulp Fiction", 1994),
    ("Interstellar", 2014), ("The Matrix", 1999), ("Titanic", 1997),
    ("Avengers: Endgame", 2019), ("Whiplash", 2014), ("Coco", 2017),
    ("Get Out", 2017), ("Joker", 2019), ("La La Land", 2016),
    ("The Shawshank Redemption", 1994), ("Fight Club", 1999), ("Gladiator", 2000),
    ("The Lion King", 1994), ("Toy Story", 1995), ("Forrest Gump", 1994),
    ("The Social Network", 2010), ("Mad Max: Fury Road", 2015),
    ("Django Unchained", 2012), ("Everything Everywhere All at Once", 2022),
]
```

Feel free to swap in 3-5 of your own favorites — just keep at least 20 titles and a mix of
genres, since Part 2's genre/decade queries are more interesting with variety.

## Requirements

### 1. Fetch by title (`t=`)

For each `(title, year)` pair, call:

```
http://www.omdbapi.com/?t=<title>&y=<year>&apikey=<your key>
```

- A successful response has `"Response": "True"`. A miss (typo, no match) has
  `"Response": "False"` and an `"Error"` message — **log it and move on**, don't crash the whole
  run over one bad title.
- Wrap each request in `try/except` for network errors (timeouts, connection errors) — log and
  continue to the next title, same "don't let one failure kill the batch" principle as above.
- Save each successful response as **pretty-printed JSON** to `data/raw/<imdbID>.json` (e.g.
  `data/raw/tt1375666.json` for Inception) — one file per movie, the raw payload untouched.

### 2. Make re-runs skip what's already fetched

If you run the script twice, the second run shouldn't re-hit the API for titles it already has.
Before fetching, check whether a file for that title already exists — the simplest approach is a
small manifest (a JSON file mapping `"title|year" → imdbID`) that you check and update as you go,
since you don't know a title's `imdbID` (and therefore its output filename) until *after* you've
fetched it once.

### 3. Be a polite API client

Add a short delay between requests (e.g. `time.sleep(0.5)`) — the free tier is rate-limited, and
hammering it back-to-back risks getting temporarily blocked.

### 4. Handle a paginated search (`s=`)

Pick one keyword or franchise (e.g. `"batman"`, `"star wars"`) and call the search endpoint:

```
http://www.omdbapi.com/?s=<keyword>&page=<n>&apikey=<your key>
```

This returns up to 10 results per page plus a `totalResults` count — **not** the full detail
record, just `Title`, `Year`, `imdbID`, `Type`, `Poster`. Loop through every page until you've
collected all of them, and save the combined list to `data/raw/search_<keyword>.json`.

You won't load these search results into the warehouse in Part 2 — this step is purely about
handling a paginated API response correctly, which is different from the single-record `t=`
lookups above.

## Grading checklist

- [ ] Reads `OMDB_API_KEY` from the environment via `python-dotenv` — no hardcoded key
- [ ] Logging configured per the Week 3 pattern (`INFO` level, timestamped) — no bare `print()`
      for status messages
- [ ] Fetches all 20+ titles by `t=`, saving each as its own pretty-printed JSON file named by
      `imdbID`
- [ ] A title OMDb can't find (`"Response": "False"`) is logged and skipped, not a crash
- [ ] Network errors are caught, logged, and don't abort the rest of the batch
- [ ] Re-running the script doesn't re-fetch titles it already has on disk
- [ ] A short delay between requests
- [ ] Paginated search implemented for at least one keyword, looping until all pages are collected
