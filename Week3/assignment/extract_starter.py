"""
extract.py
──────────
Fetches movie details from the OMDb API and lands them as raw JSON files in
data/raw/, one file per movie, named by imdbID. See extraction_assignment.md
for the full requirements.
"""

import json
import logging
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("extract.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("OMDB_API_KEY")
BASE_URL = "http://www.omdbapi.com/"

RAW_DIR = Path("data/raw")
MANIFEST_PATH = RAW_DIR / "_manifest.json"
REQUEST_DELAY_SECONDS = 0.5

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

SEARCH_KEYWORD = "batman"  # TODO: pick your own keyword/franchise if you like


def load_manifest():
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest):
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def fetch_movie(title, year):
    """Fetch one movie by title+year. Returns the parsed JSON dict, or None on failure."""
    # TODO:
    #  1. GET BASE_URL with params {"t": title, "y": year, "apikey": API_KEY}
    #  2. wrap the request in try/except for network errors — log and return None
    #  3. check response["Response"] == "True" — if "False", log response["Error"] and return None
    #  4. return the parsed JSON dict on success
    raise NotImplementedError


def fetch_search_page(keyword, page):
    """Fetch one page of search results. Returns the parsed JSON dict, or None on failure."""
    # TODO: same shape as fetch_movie, but params {"s": keyword, "page": page, "apikey": API_KEY}
    raise NotImplementedError


def extract_movies():
    """Fetch every title in MOVIES that isn't already in the manifest, saving each to data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    for title, year in MOVIES:
        manifest_key = f"{title}|{year}"
        # TODO: skip this title if manifest_key is already in manifest — log and continue

        # TODO: call fetch_movie(title, year); if it returns None, continue to the next title

        # TODO: write the pretty-printed JSON to data/raw/<imdbID>.json

        # TODO: record manifest_key -> imdbID in manifest, save_manifest(manifest)

        time.sleep(REQUEST_DELAY_SECONDS)


def extract_search(keyword):
    """Page through every result for `keyword` and save the combined list to data/raw/."""
    all_results = []
    page = 1
    # TODO: loop calling fetch_search_page(keyword, page), extending all_results with
    #       response["Search"], incrementing page, until you've collected
    #       response["totalResults"] results (or a page comes back empty/failed)
    #       — remember the time.sleep between requests

    output_path = RAW_DIR / f"search_{keyword}.json"
    output_path.write_text(json.dumps(all_results, indent=2))
    logger.info(f"Saved {len(all_results)} search results for '{keyword}' to {output_path}")


def main():
    if not API_KEY:
        logger.critical("OMDB_API_KEY not set — add it to Week3/.env")
        raise SystemExit(1)

    extract_movies()
    extract_search(SEARCH_KEYWORD)
    logger.info("Extraction complete.")


if __name__ == "__main__":
    main()
