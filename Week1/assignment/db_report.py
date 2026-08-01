

import logging
import psycopg2
import os
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
    dbname="ride_share", user="postgres", password=os.environ.get("DB_PASSWORD", "")
)


REVENUE_BY_CITY_QUERY = """
select 
pickup_city, count(ride_id) total_rides, sum(fare_amount) total_revenue, round(avg(fare_amount)::numeric,2) avg_fare 
from rides 
GROUP BY pickup_city
order BY total_revenue desc;
"""


LOYALTY_BONUS_QUERY ="""
select 
driver_name, count(ride_status) completed_rides
from rides 
where ride_status = 'completed'
group by driver_name
having count(ride_status)>100 
order by completed_rides desc;
"""

OUTCOMES_BY_STATUS_QUERY = """
select 
ride_status, count(ride_id) ride_count, round(avg(ride_distance_km)::numeric,2) avg_distance_km
from rides
group by ride_status 
order by ride_count desc;
"""


def run_query(conn, query, label):
   
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
    for driver_name, completed_rides in rows:
        print(f"{driver_name:<20} | completed rides: {completed_rides}")


def print_outcomes_by_status(rows):
    print("\n-- Ride outcomes by status --")
    for status, count, avg_distance in rows:
        print(f"{status:<12} | rides: {count:>4} | avg distance: {avg_distance:.2f} km")


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
