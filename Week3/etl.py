import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
from dotenv import load_dotenv 


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

SOURCE_DB_CONFIG = dict(
    host=    os.getenv("SRC_DB_HOST"),
    port =   os.getenv("SRC_DB_PORT"),
    dbname = os.getenv("SRC_DB_NAME"),
    user=    os.getenv("SRC_DB_USER"),
    password=os.getenv("SRC_DB_PASSWORD")
)
DEST_DB_CONFIG = dict(
    host=    os.getenv("DEST_DB_HOST"),
    port =   os.getenv("DEST_DB_PORT"),
    dbname = os.getenv("DEST_DB_NAME"),
    user=    os.getenv("DEST_DB_USER"),
    password=os.getenv("DEST_DB_PASSWORD")
)



def extract(conn,sql):
    try:
        with conn.cursor(cursor_factory =RealDictCursor ) as curr:
            curr.execute(sql)
            rows = curr.fetchall()
            logger.info(f"Extracted {len(rows)} from the table")
        return rows
    except Exception as e:
        logger.error(str(e))
        raise 
    
def extract_driver(conn):
     extract_driver_sql = """
    SELECT
        driver_id ,
        name,
        status ,
        joined_at,
        CASE
            WHEN joined_at >= NOW() - INTERVAL '6 months'  THEN '0-6 months'
            WHEN joined_at >= NOW() - INTERVAL '1 year'    THEN '6-12 months'
            WHEN joined_at >= NOW() - INTERVAL '2 years'   THEN '1-2 years'
        ELSE '2+ years'
        END  AS tenure_bucket
    FROM
        drivers d ;
    """
     return extract(conn,extract_driver_sql)

    
def load_dim_driver(conn,driver_data):
    insert_dim_driver_sql = """
 INSERT INTO dim_driver
    (driver_id, name, status, joined_at,tenure_bucket)
    VALUES ( %(driver_id)s ,
             %(name)s,
             %(status)s,
            %(joined_at)s,
            %(tenure_bucket)s
            )
    ON CONFLICT DO NOTHING
"""
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_dim_driver_sql, driver_data)
            logger.info(f"{curr.rowcount} inserted to dim_driver")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise


def extract_passenger(conn):
    extract_passenger_sql = """
    SELECT
        passenger_id,
        name,
        status,
        created_at,
        TO_CHAR(created_at, 'YYYY-MM') AS cohort_month
    FROM
        passengers p;
    """
    return extract(conn, extract_passenger_sql)


def load_dim_passenger(conn, passenger_data):
    insert_dim_passenger_sql = """
 INSERT INTO dim_passenger
    (passenger_id, name, status, cohort_month, created_at)
    VALUES ( %(passenger_id)s,
             %(name)s,
             %(status)s,
             %(cohort_month)s,
             %(created_at)s
            )
    ON CONFLICT DO NOTHING
"""
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_dim_passenger_sql, passenger_data)
            logger.info(f"{curr.rowcount} inserted to dim_passenger")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise


def extract_location(conn):
    extract_location_sql = """
    SELECT
        location_id,
        city_name,
        state_province,
        country,
        latitude,
        longitude,
        CASE
            WHEN country <> 'USA' THEN 'International'
            WHEN state_province IN (
                'Connecticut','Maine','Massachusetts','New Hampshire','New Jersey',
                'New York','Pennsylvania','Rhode Island','Vermont'
            ) THEN 'Northeast'
            WHEN state_province IN (
                'Illinois','Indiana','Iowa','Kansas','Michigan','Minnesota',
                'Missouri','Nebraska','North Dakota','Ohio','South Dakota','Wisconsin'
            ) THEN 'Midwest'
            WHEN state_province IN (
                'Alabama','Arkansas','Delaware','Florida','Georgia','Kentucky',
                'Louisiana','Maryland','Mississippi','North Carolina','Oklahoma',
                'South Carolina','Tennessee','Texas','Virginia','West Virginia'
            ) THEN 'South'
            WHEN state_province IN (
                'Alaska','Arizona','California','Colorado','Hawaii','Idaho',
                'Montana','Nevada','New Mexico','Oregon','Utah','Washington','Wyoming'
            ) THEN 'West'
            ELSE 'International'
        END AS region
    FROM
        locations l;
    """
    return extract(conn, extract_location_sql)


def load_dim_location(conn, location_data):
    insert_dim_location_sql = """
 INSERT INTO dim_location
    (location_id, city_name, state_province, country, region, latitude, longitude)
    VALUES ( %(location_id)s,
             %(city_name)s,
             %(state_province)s,
             %(country)s,
             %(region)s,
             %(latitude)s,
             %(longitude)s
            )
    ON CONFLICT (location_id) DO NOTHING
"""
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_dim_location_sql, location_data)
            logger.info(f"{curr.rowcount} inserted to dim_location")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise


def extract_payment_method(conn):
    extract_payment_method_sql = """
    SELECT
        payment_method_id,
        name,
        type,
        is_active
    FROM
        payment_methods pm;
    """
    return extract(conn, extract_payment_method_sql)


def load_dim_payment_method(conn, payment_method_data):
    insert_dim_payment_method_sql = """
 INSERT INTO dim_payment_method
    (payment_method_id, name, type, is_active)
    VALUES ( %(payment_method_id)s,
             %(name)s,
             %(type)s,
             %(is_active)s
            )
    ON CONFLICT (payment_method_id) DO NOTHING
"""
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_dim_payment_method_sql, payment_method_data)
            logger.info(f"{curr.rowcount} inserted to dim_payment_method")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise


def extract_promo_code(conn):
    extract_promo_code_sql = """
    SELECT
        promo_code_id,
        code,
        discount_type,
        discount_value,
        is_active
    FROM
        promo_codes pc;
    """
    return extract(conn, extract_promo_code_sql)


def load_dim_promo_code(conn, promo_code_data):
    insert_dim_promo_code_sql = """
 INSERT INTO dim_promo_code
    (promo_code_id, code, discount_type, discount_value, is_active)
    VALUES ( %(promo_code_id)s,
             %(code)s,
             %(discount_type)s,
             %(discount_value)s,
             %(is_active)s
            )
    ON CONFLICT (promo_code_id) DO NOTHING
"""
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_dim_promo_code_sql, promo_code_data)
            logger.info(f"{curr.rowcount} inserted to dim_promo_code")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise

def extract_trips(conn):
    extract_trip_sql = """
      SELECT
        t.trip_id,
        t.driver_id,
        t.passenger_id,
        t.pickup_location_id,
        t.dropoff_location_id,
        t.payment_method_id,
        t.promo_code_id,
        t.base_fare,
        t.tip_amount,
        t.discount_amount,
        t.surge_multiplier,
        t.distance_km,
        t.status,
        t.requested_at,
        t.completed_at,
        t.driver_rating,
        t.passenger_rating,
        tc.cancelled_by          -- from trip_cancellations (NULL for non-cancelled)
    FROM  trips t
    LEFT JOIN trip_cancellations tc ON t.trip_id = tc.trip_id
    WHERE t.requested_at > %(watermark)s
    ORDER BY t.requested_at
        """
    return extract(conn,extract_trip_sql)

def load_lookup_dim(conn):
    logger.info("Loading lookup table into memmory")
    lookup = {}
    with conn.cursor() as curr:
        curr.execute("SELECT driver_id, driver_key FROM dim_driver")
        lookup["driver"] = {r[0]:r[1] for r in curr.fetchall()}

        curr.execute("SELECT passenger_id, passenger_key FROM dim_passenger")
        lookup["passenger"] = {r[0]:r[1] for r in curr.fetchall()}

        curr.execute("SELECT location_id, location_key FROM dim_location")
        lookup["location"] = {r[0]:r[1] for r in curr.fetchall()}

        curr.execute("SELECT payment_method_id, payment_method_key FROM dim_payment_method")
        lookup["payment_method"] = {r[0]:r[1] for r in curr.fetchall()}

        curr.execute("SELECT promo_code_id, promo_code_key FROM dim_promo_code")
        lookup["promo_code"] = {r[0]:r[1] for r in curr.fetchall()}

        curr.execute("SELECT date_key FROM dim_date")
        lookup["date"] = {r[0]: True for r in curr.fetchall()}
    return lookup

def transform(oltp_row, lookups):
    fact_rows = []
    skipped = 0
    for row in oltp_row:
        trip_id = row["trip_id"]

        date_key = int(row["requested_at"].strftime("%Y%m%d"))
        if date_key not in lookups["date"]:
            logger.warning(f"trip {trip_id}: date_key {date_key} outside of dim_date range — skipped")
            skipped += 1
            continue

        driver_key = lookups["driver"].get(row["driver_id"])
        if driver_key is None:
            logger.warning(f"trip {trip_id}: driver_id {row['driver_id']} not in dim_driver — skipped")
            skipped += 1
            continue

        passenger_key = lookups["passenger"].get(row["passenger_id"])
        if passenger_key is None:
            logger.warning(f"trip {trip_id}: passenger_id {row['passenger_id']} not in dim_passenger — skipped")
            skipped += 1
            continue

        pickup_location_key = lookups["location"].get(row["pickup_location_id"])
        if pickup_location_key is None:
            logger.warning(f"trip {trip_id}: pickup_location_id {row['pickup_location_id']} not in dim_location — skipped")
            skipped += 1
            continue

        dropoff_location_key = lookups["location"].get(row["dropoff_location_id"])
        if dropoff_location_key is None:
            logger.warning(f"trip {trip_id}: dropoff_location_id {row['dropoff_location_id']} not in dim_location — skipped")
            skipped += 1
            continue

        # payment_method_id / promo_code_id are nullable in trips (e.g. no_show trips
        # have no payment method) and fact_trips allows NULL for both — only look
        # up and skip when the OLTP row actually has a value.
        payment_method_key = None
        if row["payment_method_id"] is not None:
            payment_method_key = lookups["payment_method"].get(row["payment_method_id"])
            if payment_method_key is None:
                logger.warning(f"trip {trip_id}: payment_method_id {row['payment_method_id']} not in dim_payment_method — skipped")
                skipped += 1
                continue

        promo_code_key = None
        if row["promo_code_id"] is not None:
            promo_code_key = lookups["promo_code"].get(row["promo_code_id"])
            if promo_code_key is None:
                logger.warning(f"trip {trip_id}: promo_code_id {row['promo_code_id']} not in dim_promo_code — skipped")
                skipped += 1
                continue

        # computed column
        base_fare = row['base_fare'] or 0
        tip_amount = row["tip_amount"] or 0
        surge_multiplier = row["surge_multiplier"] or 0
        discount_amount = row["discount_amount"] or 0
        fare_amount  = round(base_fare * surge_multiplier + tip_amount - discount_amount,2)

        duration_minutes = None
        if row["status"] == "completed" and row["completed_at"]:
            delta = row["completed_at"] - row["requested_at"]
            duration_minutes = round(delta.total_seconds() / 60, 1)

        fact_rows.append({
            "source_trip_id":       trip_id,
            "date_key":             date_key,
            "driver_key":           driver_key,
            "passenger_key":        passenger_key,
            "pickup_location_key":  pickup_location_key,
            "dropoff_location_key": dropoff_location_key,
            "payment_method_key":   payment_method_key,
            "promo_code_key":       promo_code_key,
            "base_fare":            base_fare,
            "tip_amount":           tip_amount,
            "discount_amount":      discount_amount,
            "fare_amount":          fare_amount,
            "distance_km":          row["distance_km"],
            "duration_minutes":     duration_minutes,
            "driver_rating":        row["driver_rating"],
            "passenger_rating":     row["passenger_rating"],
            "surge_multiplier":     surge_multiplier,
            "requested_at":         row["requested_at"],
        })

    logger.info(f"Transformed {len(fact_rows)} rows, skipped {skipped}")
    return fact_rows


def load_fact_trips(conn, fact_data):
    insert_fact_trips_sql = """
 INSERT INTO fact_trips
    (source_trip_id, date_key, driver_key, passenger_key,
     pickup_location_key, dropoff_location_key,
     payment_method_key, promo_code_key,
     base_fare, tip_amount, discount_amount, fare_amount,
     distance_km, duration_minutes,
     driver_rating, passenger_rating,
     surge_multiplier, requested_at)
    VALUES ( %(source_trip_id)s,
             %(date_key)s,
             %(driver_key)s,
             %(passenger_key)s,
             %(pickup_location_key)s,
             %(dropoff_location_key)s,
             %(payment_method_key)s,
             %(promo_code_key)s,
             %(base_fare)s,
             %(tip_amount)s,
             %(discount_amount)s,
             %(fare_amount)s,
             %(distance_km)s,
             %(duration_minutes)s,
             %(driver_rating)s,
             %(passenger_rating)s,
             %(surge_multiplier)s,
             %(requested_at)s
            )
    ON CONFLICT (source_trip_id) DO NOTHING
"""
    if not fact_data:
        logger.info("No fact rows to load — skipping")
        return
    try:
        with conn.cursor() as curr:
            curr.executemany(insert_fact_trips_sql, fact_data)
            logger.info(f"{curr.rowcount} inserted to fact_trips")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(str(e))
        raise

def main():
    """
    Extract all dimension data from the source DB and load them into the target DB.
    """
    src_conn = psycopg2.connect(**SOURCE_DB_CONFIG)
    dst_conn = psycopg2.connect(**DEST_DB_CONFIG)
    try:
        driver_data = extract_driver(src_conn)
        load_dim_driver(dst_conn, driver_data)

        passenger_data = extract_passenger(src_conn)
        load_dim_passenger(dst_conn, passenger_data)

        location_data = extract_location(src_conn)
        load_dim_location(dst_conn, location_data)

        payment_method_data = extract_payment_method(src_conn)
        load_dim_payment_method(dst_conn, payment_method_data)

        promo_code_data = extract_promo_code(src_conn)
        load_dim_promo_code(dst_conn, promo_code_data)

        lookups = load_lookup_dim(dst_conn)
        rows = extract_trips(src_conn)
        fact_rows = transform(rows, lookups)
        load_fact_trips(dst_conn, fact_rows)

    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    main()

