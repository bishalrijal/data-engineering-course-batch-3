import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

SRC_DB_CONFIG = {
    "host":     os.getenv("SRC_DB_HOST", "localhost"),
    "port":     os.getenv("SRC_DB_PORT", 5432),
    "dbname":   os.getenv("SRC_DB_NAME", "ride_prod"),
    "user":     os.getenv("SRC_DB_USER", "postgres"),
    "password": os.getenv("SRC_DB_PASSWORD", "postgres"),
}

DST_DB_CONFIG = {
    "host":     os.getenv("DST_DB_HOST", "localhost"),
    "port":     os.getenv("DST_DB_PORT", 5432),
    "dbname":   os.getenv("DST_DB_NAME", "ride_dw"),
    "user":     os.getenv("DST_DB_USER", "postgres"),
    "password": os.getenv("DST_DB_PASSWORD", "postgres"),
}

# Tables copied 1:1 into ride_dw.raw as-is. No transformation here — that's dbt's job.
RAW_TABLES = [
    "drivers",
    "passengers",
    "locations",
    "payment_methods",
    "promo_codes",
    "trips",
    "trip_cancellations",
]


def column_ddl(col):
    name, data_type, char_len, num_precision, num_scale = col
    if data_type == "character varying":
        col_type = f"varchar({char_len})" if char_len else "varchar"
    elif data_type == "numeric" and num_precision is not None:
        col_type = f"numeric({num_precision},{num_scale})"
    else:
        col_type = data_type
    return f'"{name}" {col_type}'


def get_columns(src_conn, table):
    with src_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, character_maximum_length,
                   numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return cur.fetchall()


def load_table(src_conn, dst_conn, table):
    columns = get_columns(src_conn, table)
    col_names = [c[0] for c in columns]

    with dst_conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw")
        ddl = ", ".join(column_ddl(c) for c in columns)
        cur.execute(f'CREATE TABLE IF NOT EXISTS raw."{table}" ({ddl})')
        cur.execute(f'TRUNCATE raw."{table}"')

    with src_conn.cursor() as cur:
        cur.execute(f'SELECT {", ".join(col_names)} FROM "{table}"')
        rows = cur.fetchall()

    if rows:
        with dst_conn.cursor() as cur:
            cols_sql = ", ".join(f'"{c}"' for c in col_names)
            execute_values(
                cur, f'INSERT INTO raw."{table}" ({cols_sql}) VALUES %s', rows
            )

    print(f"{table}: {len(rows)} rows loaded into raw.{table}")


def main():
    src_conn = psycopg2.connect(**SRC_DB_CONFIG)
    dst_conn = psycopg2.connect(**DST_DB_CONFIG)
    try:
        for table in RAW_TABLES:
            load_table(src_conn, dst_conn, table)
        dst_conn.commit()
    except Exception:
        dst_conn.rollback()
        raise
    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    main()
