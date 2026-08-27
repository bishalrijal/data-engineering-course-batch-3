
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "data-eng",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def is_weekend(**context):
    """Stand-in condition - swap for any real business logic."""
    execution_day = context["logical_date"]
    return execution_day.weekday() >= 5


def choose_branch(**context):
    """Must return the task_id(s) of whichever downstream path should run."""
    if is_weekend(**context):
        return "light_job"
    return "full_job"


def light_job(**context):
    print("Running the lightweight weekend job...")


def full_job(**context):
    print("Running the full weekday job...")
    # Uncomment to see the one_failed branch fire in class:
    # raise ValueError("Simulated failure")


def notify_success(**context):
    print("Pipeline finished - sending a success notification.")


def alert_on_failure(**context):
    print("Something upstream failed - sending an alert.")


with DAG(
    dag_id="branching_and_trigger_rules_demo",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["day2", "demo"],
) as dag:

    branch = BranchPythonOperator(
        task_id="choose_branch",
        python_callable=choose_branch,
    )

    light_job_task = PythonOperator(task_id="light_job", python_callable=light_job)
    full_job_task = PythonOperator(task_id="full_job", python_callable=full_job)

    # Default trigger_rule is "all_success", which would never fire here
    # because only ONE of the two branches actually runs (the other is
    # skipped). "none_failed" means: run as long as nothing that DID run
    # failed - skips are fine.
    notify_success_task = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
        trigger_rule=TriggerRule.NONE_FAILED,
    )

    # # This task should run precisely when something goes wrong upstream,
    # # regardless of which branch was taken.
    alert_task = PythonOperator(
        task_id="alert_on_failure",
        python_callable=alert_on_failure,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    branch >> [light_job_task, full_job_task]
    [light_job_task, full_job_task] >> notify_success_task
    [light_job_task, full_job_task] >> alert_task
