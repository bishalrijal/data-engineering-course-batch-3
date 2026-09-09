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
    dbname="ride_share", user="postgres", password="2017012"
)

# TODO: fill in each query to match Q6 / Q7 / Q8 from sql_assignment.md
REVENUE_BY_CITY_QUERY = """
    -- Q6: pickup_city, total_rides, total_revenue, avg_fare

    select 
        pickup_city, 
        count(*) as total_rides, 
        sum(fare_amount) as total_revenue, 
        round(avg(fare_amount),2) as avg_fare 
    from rides r 
    group by pickup_city
    order by total_revenue desc;
"""

LOYALTY_BONUS_QUERY = """
    -- Q7: driver_name, completed_rides — more than 100 completed rides

    select 
        driver_name, 
        count(*) as completed_rides
    from rides r
    where ride_status='completed'
    group by driver_name
    having count(*)>=100
    order by count(*) desc;
"""

OUTCOMES_BY_STATUS_QUERY = """
    -- Q8: ride_status, ride_count, avg_distance_km

    select
        ride_status, 
        count(*) as ride_count, 
        round(avg(ride_distance_km), 2) as avg_distance_km
    from rides r
    group by ride_status
    order by count(*) desc;
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
    # f"{city:<15} | rides: {count:>4} | revenue: NPR {revenue:,.2f} | avg fare: NPR {avg_fare:,.2f}"
    for row in rows:
        city, count, revenue, avg_fare = row
        print(f"{city:<15} | rides: {count:>4} | revenue: NPR {revenue:,.2f} | avg fare: NPR {avg_fare:,.2f}")

def print_loyalty_bonus(rows):
    print("\n-- Drivers who qualify for the loyalty bonus --")
    # TODO: loop over rows and print each one formatted
    for row in rows:
        driver_name, completed_rides = row
        print(f"{driver_name:<20} | completed rides: {completed_rides:>4}")


def print_outcomes_by_status(rows):
    print("\n-- Ride outcomes by status --")
    # TODO: loop over rows and print each one formatted
    for row in rows:
        status, count, avg_dist = row
        print(f"{status:<15} | total: {count:>5} | avg distance: {avg_dist:>5.2f} km")
        


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
