"""
Rides ETL DAG — extracts dimension and trip data from the OLTP database
(ride_sharing_oltp connection), transforms trips into fact rows, runs the
quality gate, and loads everything into the ride_dw warehouse
(ride_sharing_warehouse connection).

Mirrors the extract -> transform -> quality -> load flow in Week5/pipeline.py.
Set the "full_reload" DAG param to truncate/reload every trip instead of the
default incremental (watermark-based) load.
"""

from datetime import datetime, timedelta

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import DAG, Param, task

from pipeline.extract import (
    extract_driver,
    extract_passenger,
    extract_location,
    extract_payment_method,
    extract_promo_code,
    extract_trips_incremental,
    extract_trips_full,
    extract_lookup_dim,
    get_watermark,
)
from pipeline.load import (
    load_dim_driver,
    load_dim_passenger,
    load_dim_location,
    load_dim_payment_method,
    load_dim_promo_code,
    load_fact_trips,
)
from pipeline.transform import transform
from pipeline.quality import run_quality_checks

SRC_CONN_ID = "ride_sharing_oltp"
DEST_CONN_ID = "ride_sharing_warehouse"


with DAG(
    dag_id="ride_db_to_dw",
    description="Extract rides OLTP data, transform, and load into the ride_dw warehouse",
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={
        "full_reload": Param(
            False,
            type="boolean",
            description="Truncate-reload every trip instead of the default incremental load",
        ),
    },
    tags=["rides", "etl"],
) as dag:

    @task
    def load_dim_drivers():
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            load_dim_driver(dst, extract_driver(src))
        finally:
            src.close()
            dst.close()

    @task
    def load_dim_passengers():
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            load_dim_passenger(dst, extract_passenger(src))
        finally:
            src.close()
            dst.close()

    @task
    def load_dim_locations():
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            load_dim_location(dst, extract_location(src))
        finally:
            src.close()
            dst.close()

    @task
    def load_dim_payment_methods():
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            load_dim_payment_method(dst, extract_payment_method(src))
        finally:
            src.close()
            dst.close()

    @task
    def load_dim_promo_codes():
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            load_dim_promo_code(dst, extract_promo_code(src))
        finally:
            src.close()
            dst.close()

    @task
    def extract_transform_load_fact_trips(**context):
        full_reload = context["params"]["full_reload"]
        src, dst = PostgresHook(SRC_CONN_ID).get_conn(), PostgresHook(DEST_CONN_ID).get_conn()
        try:
            lookups = extract_lookup_dim(dst)

            if full_reload:
                rows = extract_trips_full(src)
            else:
                watermark = get_watermark(dst)
                rows = extract_trips_incremental(src, {"watermark": watermark})

            fact_rows = transform(rows, lookups)
            run_quality_checks(fact_rows)
            load_fact_trips(dst, fact_rows, full_reload=full_reload)
        finally:
            src.close()
            dst.close()

    dim_tasks = [
        load_dim_drivers(),
        load_dim_passengers(),
        load_dim_locations(),
        load_dim_payment_methods(),
        load_dim_promo_codes(),
    ]

    dim_tasks >> extract_transform_load_fact_trips()
