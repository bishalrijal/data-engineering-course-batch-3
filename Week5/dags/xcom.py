from airflow.sdk import DAG
from datetime import datetime

from datetime import timedelta

from airflow.providers.standard.operators.python import PythonOperator

from airflow.utils.trigger_rule import TriggerRule


from airflow.sdk import BaseOperator

class SlackMessageOperator(BaseOperator):
    def __init__(self,message,**kwarg):
        super().__init__(**kwarg)
        self.message = message

    def execute(self, context):
        print(self.message)
        # API call to post message on slack
        return self.message


def python_transform(**context):
    row_from_extract =context["ti"].xcom_pull(task_ids="extract",key="row_count")
    print(row_from_extract)
    print("hello! Transform from python")
    return row_from_extract

def python_transform2():
    raise

def python_extract(**context):
    row_count = 5000
    context["ti"].xcom_push(key = "row_count", value=row_count)
    print("this is extract function")

def python_load():
    print("this is extract function")

def send_success():
    print("pipeline execute successfully")


def send_failure():
    print("pipeline failed")

with DAG(description="This is demo dag for xcom",
         dag_id='xcom_demo',
         schedule='@daily') as dag:
    extract = PythonOperator(task_id = 'extract', python_callable= python_extract)
    trasnsform = PythonOperator(task_id='transform', python_callable=python_transform)
    trasnsform2 = PythonOperator(task_id='transform2', python_callable=python_transform2)

    load = PythonOperator(task_id = 'load',python_callable=python_load)

    success_message = SlackMessageOperator(task_id='success', message="pipeline executed successfully", trigger_rule = TriggerRule.ALL_SUCCESS)
    failure_message = SlackMessageOperator(task_id='failure', message="pipeline failed", trigger_rule=TriggerRule.ONE_FAILED)
    extract >> [trasnsform,trasnsform2] >> load >> [success_message, failure_message]
