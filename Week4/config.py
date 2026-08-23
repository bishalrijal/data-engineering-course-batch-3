import os
from dotenv import load_dotenv
load_dotenv()

SOURCE_DB_CONFIG = dict(
    host=    os.getenv("SRC_DB_HOST"),
    port =   os.getenv("SRC_DB_PORT"),
    dbname = os.getenv("SRC_DB_NAME"),
    user=    os.getenv("SRC_DB_USER"),
    password=os.getenv("SRC_DB_PASSWORD")
)
DEST_DB_CONFIG = dict(
    host=    os.getenv("DST_DB_HOST"),
    port =   os.getenv("DST_DB_PORT"),
    dbname = os.getenv("DST_DB_NAME"),
    user=    os.getenv("DST_DB_USER"),
    password=os.getenv("DST_DB_PASSWORD")
)
