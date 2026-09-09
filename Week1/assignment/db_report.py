"""
db_report.py
────────────
Connects to the ride_share database and prints the results of the three
aggregation questions (Q6, Q7, Q8) from the Week 1 SQL assignment.
"""

import logging
import psycopg2

# ── Logging setup — same pattern as the Python pre-read ──────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ── Database config ────────────────────────────────────────────────────────
DB_CONFIG = dict(
    host="localhost", port=5432,
    dbname="postgres", user="postgres", password="kri@2004"
)

# TODO: fill in each query to match Q6 / Q7 / Q8 from sql_assignment.md
REVENUE_BY_CITY_QUERY = """
SELECT pickup_city,
       COUNT(*) AS total_rides,
       SUM(fare_amount) AS total_revenue,
       ROUND(AVG(fare_amount),2) AS avg_fare
FROM rides
GROUP BY pickup_city
ORDER BY total_revenue DESC;
"""

LOYALTY_BONUS_QUERY = """
SELECT driver_name,
       COUNT(*) AS completed_rides
FROM rides
WHERE ride_status = 'completed'
GROUP BY driver_name
HAVING COUNT(*) > 100
ORDER BY completed_rides DESC;
"""

OUTCOMES_BY_STATUS_QUERY = """
SELECT ride_status,
       COUNT(*) AS ride_count,
       ROUND(AVG(ride_distance_km),2) AS avg_distance_km
FROM rides
GROUP BY ride_status
ORDER BY ride_count DESC;
"""


def run_query(conn, query, label):
    """Run one query, log progress, and return the fetched rows."""
    logger.info(f"Running: {label}")
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"{label} failed: {e}")
        raise

    logger.info(f"{label}: {len(rows)} rows returned")
    return rows


def print_revenue_by_city(rows):
    print("\n-- Revenue by pickup city --")
    for city, count, revenue, avg_fare in rows:
     print(f"{city:<15} | rides: {count:>4} | revenue: NPR {revenue:,.2f} | avg fare: NPR {avg_fare:,.2f}")


def print_loyalty_bonus(rows):
    print("\n-- Drivers who qualify for the loyalty bonus --")
    for driver, completed_rides in rows:
     print(f"{driver:<25} | completed rides: {completed_rides}")


def print_outcomes_by_status(rows):
    print("\n-- Ride outcomes by status --")
    for status, ride_count, avg_distance in rows:
     print(f"{status:<12} | rides: {ride_count:>4} | avg distance: {avg_distance:.2f} km")


def main():
    logger.info("Connecting to database…")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        logger.critical(f"Cannot connect: {e}")
        raise

    try:
        rows = run_query(conn, REVENUE_BY_CITY_QUERY, "Revenue by city")
        print_revenue_by_city(rows)

        rows = run_query(conn, LOYALTY_BONUS_QUERY, "Loyalty bonus drivers")
        print_loyalty_bonus(rows)

        rows = run_query(conn, OUTCOMES_BY_STATUS_QUERY, "Outcomes by status")
        print_outcomes_by_status(rows)
    finally:
        conn.close()
        logger.info("Connection closed. Done.")


if __name__ == "__main__":
    main()
