### NABINA KHADKA - ASSIGNMENT 1 - PYTHON ###

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
    host="localhost", port=5434,
    dbname="ride_share", user="postgres", password=""
)

# TODO: fill in each query to match Q6 / Q7 / Q8 from sql_assignment.md
REVENUE_BY_CITY_QUERY = """
    -- Q6: pickup_city, total_rides, total_revenue, avg_fare

    SELECT pickup_city, count(*) AS total_rides , sum(fare_amount) AS total_revenue , 
    round(avg(fare_amount),2) AS avg_fare
    FROM rides
    GROUP BY pickup_city
    ORDER BY total_revenue DESC;

"""

LOYALTY_BONUS_QUERY = """
    -- Q7: driver_name, completed_rides — more than 100 completed rides

    SELECT driver_name , count(*) AS completed_rides FROM rides
    WHERE ride_status = 'completed'
    GROUP BY driver_name
    HAVING count(*) > 100
    ORDER BY completed_rides desc
"""

OUTCOMES_BY_STATUS_QUERY = """
    -- Q8: ride_status, ride_count, avg_distance_km

    SELECT ride_status, count(*) AS ride_count, round(avg(ride_distance_km),2) AS avg_distance_km
    FROM rides
    GROUP BY ride_status
    ORDER BY ride_count desc
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
    # TODO: loop over rows and print each one formatted, e.g.
    for city, count, revenue, avg_fare in rows:
        print(f"{city:<15} | rides: {count:>4} | revenue: NPR {revenue:,.2f} | avg fare: NPR {avg_fare:,.2f}")


def print_loyalty_bonus(rows):
    print("\n-- Drivers who qualify for the loyalty bonus --")
    # TODO: loop over rows and print each one formatted
    for driver, completed_rides in rows:
        print(f"{driver:<20} | completed rides: {completed_rides:>4}")

def print_outcomes_by_status(rows):
    print("\n-- Ride outcomes by status --")
    # TODO: loop over rows and print each one formatted
    for status, ride_count, avg_distance_km in rows:
        print(f"{status:<15} | ride count: {ride_count:>4} | avg distance: {avg_distance_km:,.2f} km")

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