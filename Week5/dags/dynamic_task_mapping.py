
from datetime import datetime, timedelta

from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def extract(**context):
    print("Extracting raw data...")


def clean(**context):
    print("Cleaning records...")


def dedupe(**context):
    print("Removing duplicate records...")


def load(**context):
    print("Loading cleaned data into the warehouse...")


# Stand-in for "list of files that showed up today" - in real life this
# might come from an S3 listing, a database query, or an upstream XCom.
def list_files():
    return ["orders_2026_01_01.csv", "orders_2026_01_02.csv", "orders_2026_01_03.csv"]


@task
def process_file(path: str):
    """One mapped task instance is created per item list_files() returns."""
    print(f"Processing file: {path}")


with DAG(
    dag_id="taskgroups_and_dynamic_mapping_demo",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["day2", "demo"],
) as dag:

    extract_task = PythonOperator(task_id="extract", python_callable=extract)

    # --- TaskGroup: purely organizational, collapses to one node in the UI ---
    # with TaskGroup("transform") as transform_group:
    #     clean_task = PythonOperator(task_id="clean", python_callable=clean)
    #     dedupe_task = PythonOperator(task_id="dedupe", python_callable=dedupe)
    #     clean_task >> dedupe_task

    load_task = PythonOperator(task_id="load", python_callable=load)

    # extract_task >> transform_group >> load_task

    # --- Dynamic Task Mapping: one task instance per file, decided at runtime ---
    # process_file.expand(path=list_files())
    load_task >> process_file.expand(path=list_files())

    # Talking point for class: process_file's mapped instances run independently
    # of the extract >> transform >> load chain above. Ask students how they'd
    # wire process_file.expand(...) to run only *after* load_task succeeds
    # (Answer: load_task >> process_file.expand(path=list_files())).