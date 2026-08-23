import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import SOURCE_DB_CONFIG,DEST_DB_CONFIG

import time

from extract import (extract_driver,
                     extract_passenger,
                     extract_lookup_dim,
                     extract_promo_code,
                     extract_payment_method,
                     extract_location,
                     extract_trips,
                     get_watermark
                     )
from transform import transform
from quality import run_quality_check

from load import (
    load_fact_trips,
    load_dim_promo_code,
    load_dim_passenger,
    load_dim_payment_method,
    load_dim_location,
    load_dim_driver
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s %(filename)s:%(lineno)d   %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """
    Extract all dimension data from the source DB and load them into the target DB.
    """
    is_full_load = True
    src_conn = psycopg2.connect(**SOURCE_DB_CONFIG)
    dst_conn = psycopg2.connect(**DEST_DB_CONFIG)
    try:
        time0 = time.time()
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

        time1 = time.time()
        logger.info(f"Dimension sync completed on {time1-time0:.3f}s")

        time0 = time.time()
        lookups = extract_lookup_dim(dst_conn)
        logger.info(f"lookup ectraction completd on {time.time() - time0:.3f}s")

        watermark = get_watermark(dst_conn)
        rows = extract_trips(src_conn,{"watermark":watermark})
        fact_rows = transform(rows, lookups)
        run_quality_check(rows)
        load_fact_trips(dst_conn, fact_rows)

    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    main()

