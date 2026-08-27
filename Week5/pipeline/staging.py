"""
staging.py
----------
Staging-table logic for the extract-load-transform (ELT) staging pattern
used by dags/fact_trips_via_staging.py: DDL, per-dimension config, and the
stage/read helpers that move rows through warehouse staging tables scoped
by batch_id, instead of through XCom.

Every stage/read helper takes an already-open connection and a batch_id
(the Airflow run_id) — callers own connection lifecycle and transactions
stay scoped to a single delete-then-insert per call, so a task retry never
double-inserts.
"""

from psycopg2.extras import RealDictCursor

from pipeline.extract import (
    extract_driver,
    extract_passenger,
    extract_location,
    extract_payment_method,
    extract_promo_code,
)
from pipeline.load import (
    load_dim_driver,
    load_dim_passenger,
    load_dim_location,
    load_dim_payment_method,
    load_dim_promo_code,
)

# Each dimension staged identically: extract from OLTP -> stg_dim_<key>,
# then load stg_dim_<key> -> the real dim_<key> table. Column lists match
# what the corresponding extract_*/load_dim_* pair in pipeline/ already
# produces/expects.
DIM_CONFIGS = [
    dict(
        key="driver",
        staging_table="stg_dim_driver",
        columns=["driver_id", "name", "status", "joined_at", "tenure_bucket"],
        extract_fn=extract_driver,
        load_fn=load_dim_driver,
    ),
    dict(
        key="passenger",
        staging_table="stg_dim_passenger",
        columns=["passenger_id", "name", "status", "created_at", "cohort_month"],
        extract_fn=extract_passenger,
        load_fn=load_dim_passenger,
    ),
    dict(
        key="location",
        staging_table="stg_dim_location",
        columns=["location_id", "city_name", "state_province", "country", "latitude", "longitude", "region"],
        extract_fn=extract_location,
        load_fn=load_dim_location,
    ),
    dict(
        key="payment_method",
        staging_table="stg_dim_payment_method",
        columns=["payment_method_id", "name", "type", "is_active"],
        extract_fn=extract_payment_method,
        load_fn=load_dim_payment_method,
    ),
    dict(
        key="promo_code",
        staging_table="stg_dim_promo_code",
        columns=["promo_code_id", "code", "discount_type", "discount_value", "is_active"],
        extract_fn=extract_promo_code,
        load_fn=load_dim_promo_code,
    ),
]

DIM_STAGING_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS stg_dim_driver (
        batch_id       TEXT          NOT NULL,
        driver_id      INTEGER       NOT NULL,
        name           VARCHAR(100),
        status         VARCHAR(20),
        joined_at      TIMESTAMP,
        tenure_bucket  VARCHAR(20),
        staged_at      TIMESTAMP     NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_dim_driver_batch ON stg_dim_driver(batch_id);",
    """
    CREATE TABLE IF NOT EXISTS stg_dim_passenger (
        batch_id      TEXT          NOT NULL,
        passenger_id  INTEGER       NOT NULL,
        name          VARCHAR(100),
        status        VARCHAR(20),
        created_at    TIMESTAMP,
        cohort_month  VARCHAR(7),
        staged_at     TIMESTAMP     NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_dim_passenger_batch ON stg_dim_passenger(batch_id);",
    """
    CREATE TABLE IF NOT EXISTS stg_dim_location (
        batch_id        TEXT          NOT NULL,
        location_id     INTEGER       NOT NULL,
        city_name       VARCHAR(100),
        state_province  VARCHAR(100),
        country         VARCHAR(100),
        latitude        NUMERIC(9,6),
        longitude       NUMERIC(9,6),
        region          VARCHAR(30),
        staged_at       TIMESTAMP     NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_dim_location_batch ON stg_dim_location(batch_id);",
    """
    CREATE TABLE IF NOT EXISTS stg_dim_payment_method (
        batch_id            TEXT          NOT NULL,
        payment_method_id   INTEGER,
        name                VARCHAR(30),
        type                VARCHAR(20),
        is_active           BOOLEAN,
        staged_at           TIMESTAMP     NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_dim_payment_method_batch ON stg_dim_payment_method(batch_id);",
    """
    CREATE TABLE IF NOT EXISTS stg_dim_promo_code (
        batch_id        TEXT          NOT NULL,
        promo_code_id   INTEGER,
        code            VARCHAR(30),
        discount_type   VARCHAR(10),
        discount_value  NUMERIC(8,2),
        is_active       BOOLEAN,
        staged_at       TIMESTAMP     NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_dim_promo_code_batch ON stg_dim_promo_code(batch_id);",
]

FACT_STAGING_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS stg_trip_extract (
        batch_id             TEXT        NOT NULL,
        trip_id              INTEGER     NOT NULL,
        driver_id            INTEGER,
        passenger_id         INTEGER,
        pickup_location_id   INTEGER,
        dropoff_location_id  INTEGER,
        payment_method_id    INTEGER,
        promo_code_id        INTEGER,
        base_fare            NUMERIC(10,2),
        tip_amount           NUMERIC(8,2),
        discount_amount      NUMERIC(8,2),
        surge_multiplier     NUMERIC(4,2),
        distance_km          NUMERIC(6,2),
        status               VARCHAR(20),
        requested_at         TIMESTAMP,
        completed_at         TIMESTAMP,
        driver_rating        NUMERIC(2,1),
        passenger_rating     NUMERIC(2,1),
        cancelled_by         VARCHAR(20),
        staged_at            TIMESTAMP   NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_trip_extract_batch ON stg_trip_extract(batch_id);",
    """
    CREATE TABLE IF NOT EXISTS stg_fact_trips (
        batch_id                TEXT            NOT NULL,
        source_trip_id          INTEGER         NOT NULL,
        date_key                INTEGER,
        driver_key               INTEGER,
        passenger_key            INTEGER,
        pickup_location_key      INTEGER,
        dropoff_location_key     INTEGER,
        payment_method_key       INTEGER,
        promo_code_key           INTEGER,
        base_fare                NUMERIC(10,2),
        tip_amount               NUMERIC(8,2),
        discount_amount          NUMERIC(8,2),
        fare_amount              NUMERIC(10,2),
        distance_km              NUMERIC(6,2),
        status                   VARCHAR(20),
        duration_minutes         NUMERIC(6,1),
        driver_rating            NUMERIC(2,1),
        passenger_rating         NUMERIC(2,1),
        surge_multiplier         NUMERIC(4,2),
        requested_at             TIMESTAMP,
        staged_at                TIMESTAMP       NOT NULL DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_stg_fact_trips_batch ON stg_fact_trips(batch_id);",
]

STAGING_TABLES_SQL = DIM_STAGING_TABLES_SQL + FACT_STAGING_TABLES_SQL

STAGING_TABLES = [cfg["staging_table"] for cfg in DIM_CONFIGS] + ["stg_trip_extract", "stg_fact_trips"]

INSERT_STG_TRIP_EXTRACT_SQL = """
    INSERT INTO stg_trip_extract (
        batch_id, trip_id, driver_id, passenger_id, pickup_location_id, dropoff_location_id,
        payment_method_id, promo_code_id, base_fare, tip_amount, discount_amount,
        surge_multiplier, distance_km, status, requested_at, completed_at,
        driver_rating, passenger_rating, cancelled_by
    ) VALUES (
        %(batch_id)s, %(trip_id)s, %(driver_id)s, %(passenger_id)s, %(pickup_location_id)s, %(dropoff_location_id)s,
        %(payment_method_id)s, %(promo_code_id)s, %(base_fare)s, %(tip_amount)s, %(discount_amount)s,
        %(surge_multiplier)s, %(distance_km)s, %(status)s, %(requested_at)s, %(completed_at)s,
        %(driver_rating)s, %(passenger_rating)s, %(cancelled_by)s
    )
"""

SELECT_STG_TRIP_EXTRACT_SQL = """
    SELECT trip_id, driver_id, passenger_id, pickup_location_id, dropoff_location_id,
           payment_method_id, promo_code_id, base_fare, tip_amount, discount_amount,
           surge_multiplier, distance_km, status, requested_at, completed_at,
           driver_rating, passenger_rating, cancelled_by
    FROM stg_trip_extract
    WHERE batch_id = %(batch_id)s
    ORDER BY requested_at
"""

INSERT_STG_FACT_TRIPS_SQL = """
    INSERT INTO stg_fact_trips (
        batch_id, source_trip_id, date_key, driver_key, passenger_key,
        pickup_location_key, dropoff_location_key, payment_method_key, promo_code_key,
        base_fare, tip_amount, discount_amount, fare_amount, distance_km, status,
        duration_minutes, driver_rating, passenger_rating, surge_multiplier, requested_at
    ) VALUES (
        %(batch_id)s, %(source_trip_id)s, %(date_key)s, %(driver_key)s, %(passenger_key)s,
        %(pickup_location_key)s, %(dropoff_location_key)s, %(payment_method_key)s, %(promo_code_key)s,
        %(base_fare)s, %(tip_amount)s, %(discount_amount)s, %(fare_amount)s, %(distance_km)s, %(status)s,
        %(duration_minutes)s, %(driver_rating)s, %(passenger_rating)s, %(surge_multiplier)s, %(requested_at)s
    )
"""

SELECT_STG_FACT_TRIPS_SQL = """
    SELECT source_trip_id, date_key, driver_key, passenger_key,
           pickup_location_key, dropoff_location_key, payment_method_key, promo_code_key,
           base_fare, tip_amount, discount_amount, fare_amount, distance_km, status,
           duration_minutes, driver_rating, passenger_rating, surge_multiplier, requested_at
    FROM stg_fact_trips
    WHERE batch_id = %(batch_id)s
"""


def stage_dim_rows(conn, table, columns, rows, batch_id):
    """Delete-then-insert this batch's rows into a dimension staging table."""
    for row in rows:
        row["batch_id"] = batch_id

    col_list = ", ".join(["batch_id"] + columns)
    placeholders = ", ".join(f"%({c})s" for c in ["batch_id"] + columns)
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE batch_id = %(batch_id)s", {"batch_id": batch_id})
        if rows:
            cur.executemany(insert_sql, rows)
    conn.commit()


def read_dim_staged_rows(conn, table, batch_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM {table} WHERE batch_id = %(batch_id)s", {"batch_id": batch_id})
        return cur.fetchall()


def stage_trip_extract_rows(conn, rows, batch_id):
    for row in rows:
        row["batch_id"] = batch_id

    with conn.cursor() as cur:
        cur.execute("DELETE FROM stg_trip_extract WHERE batch_id = %(batch_id)s", {"batch_id": batch_id})
        if rows:
            cur.executemany(INSERT_STG_TRIP_EXTRACT_SQL, rows)
    conn.commit()


def read_trip_extract_rows(conn, batch_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SELECT_STG_TRIP_EXTRACT_SQL, {"batch_id": batch_id})
        return cur.fetchall()


def stage_fact_trips_rows(conn, fact_rows, batch_id):
    for row in fact_rows:
        row["batch_id"] = batch_id

    with conn.cursor() as cur:
        cur.execute("DELETE FROM stg_fact_trips WHERE batch_id = %(batch_id)s", {"batch_id": batch_id})
        if fact_rows:
            cur.executemany(INSERT_STG_FACT_TRIPS_SQL, fact_rows)
    conn.commit()


def read_fact_trips_rows(conn, batch_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SELECT_STG_FACT_TRIPS_SQL, {"batch_id": batch_id})
        return cur.fetchall()


def cleanup_staging_rows(conn, batch_id):
    """Delete this run's rows from every staging table. Called with
    trigger_rule="all_done" so staging rows don't accumulate on failure.
    """
    with conn.cursor() as cur:
        for table in STAGING_TABLES:
            cur.execute(f"DELETE FROM {table} WHERE batch_id = %(batch_id)s", {"batch_id": batch_id})
    conn.commit()
