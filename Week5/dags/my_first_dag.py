from airflow.sdk import DAG
from datetime import datetime

from datetime import timedelta

from airflow.providers.standard.operators.bash import BashOperator

from airflow.providers.standard.operators.python import PythonOperator

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

def trasnform_data():
    print("transfrom from python 1")

def transform_data_2():
    print("transfrom from python 2")



with DAG(
    description="This is my first sample dag for etl",
    dag_id='my_first_dag', 
    start_date=datetime(2026,1,1),
    schedule= '@daily'
) as dag:
    extract = BashOperator(task_id='extract',bash_command='echo "extract"')
    transform1 = PythonOperator(task_id='transform',python_callable=trasnform_data,retries=3,retry_delay = timedelta(seconds= 5) )
    trasform2 = PythonOperator(task_id = 'transform_2', python_callable= transform_data_2)
    load    = SQLExecuteQueryOperator(task_id='load',sql=["select 'hello'"], conn_id='ride_sharing_warehouse')
    extract >> [transform1, trasform2] >> load