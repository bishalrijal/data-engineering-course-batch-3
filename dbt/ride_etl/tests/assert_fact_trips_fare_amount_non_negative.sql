-- fare_amount = (base_fare * surge) + tip - discount should never go negative
select *
from {{ ref('fact_trips') }}
where fare_amount < 0
