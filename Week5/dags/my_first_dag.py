from airflow.sdk import DAG
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator

with DAG(
    dag_id='my_first_dag', 
    start_date=datetime(2026,1,1)
) as dag:
    extract = BashOperator(task_id='extract',bash_command='echo "extract"')
    load    = BashOperator(task_id='load',bash_command='echo "loading"')
    extract >> load