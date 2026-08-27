import logging

logger = logging.getLogger(__name__)


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
    ON CONFLICT (driver_id) DO UPDATE SET
        name = EXCLUDED.name,
        status = EXCLUDED.status,
        joined_at = EXCLUDED.joined_at,
        tenure_bucket = EXCLUDED.tenure_bucket
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
    ON CONFLICT (passenger_id) DO UPDATE SET
        name = EXCLUDED.name,
        status = EXCLUDED.status,
        cohort_month = EXCLUDED.cohort_month,
        created_at = EXCLUDED.created_at
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
    ON CONFLICT (location_id) DO UPDATE SET
        city_name = EXCLUDED.city_name,
        state_province = EXCLUDED.state_province,
        country = EXCLUDED.country,
        region = EXCLUDED.region,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude
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


def load_dim_payment_method(conn, payment_method_data):
    insert_dim_payment_method_sql = """
 INSERT INTO dim_payment_method
    (payment_method_id, name, type, is_active)
    VALUES ( %(payment_method_id)s,
             %(name)s,
             %(type)s,
             %(is_active)s
            )
    ON CONFLICT (payment_method_id) DO UPDATE SET
        name = EXCLUDED.name,
        type = EXCLUDED.type,
        is_active = EXCLUDED.is_active
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
    ON CONFLICT (promo_code_id) DO UPDATE SET
        code = EXCLUDED.code,
        discount_type = EXCLUDED.discount_type,
        discount_value = EXCLUDED.discount_value,
        is_active = EXCLUDED.is_active
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


def load_fact_trips(conn, fact_data, full_reload=False):
    if full_reload:
        conflict_clause = """
    ON CONFLICT (source_trip_id) DO UPDATE SET
        date_key = EXCLUDED.date_key,
        driver_key = EXCLUDED.driver_key,
        passenger_key = EXCLUDED.passenger_key,
        pickup_location_key = EXCLUDED.pickup_location_key,
        dropoff_location_key = EXCLUDED.dropoff_location_key,
        payment_method_key = EXCLUDED.payment_method_key,
        promo_code_key = EXCLUDED.promo_code_key,
        base_fare = EXCLUDED.base_fare,
        tip_amount = EXCLUDED.tip_amount,
        discount_amount = EXCLUDED.discount_amount,
        fare_amount = EXCLUDED.fare_amount,
        distance_km = EXCLUDED.distance_km,
        duration_minutes = EXCLUDED.duration_minutes,
        driver_rating = EXCLUDED.driver_rating,
        passenger_rating = EXCLUDED.passenger_rating,
        surge_multiplier = EXCLUDED.surge_multiplier,
        requested_at = EXCLUDED.requested_at
"""
    else:
        conflict_clause = "\n    ON CONFLICT (source_trip_id) DO NOTHING\n"

    insert_fact_trips_sql = f"""
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
{conflict_clause}"""
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
