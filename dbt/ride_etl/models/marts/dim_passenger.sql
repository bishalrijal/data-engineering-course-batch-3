select
    row_number() over (order by passenger_id) as passenger_key,
    passenger_id,
    name,
    status,
    to_char(created_at, 'YYYY-MM') as cohort_month,
    created_at
from {{ ref('stg_passengers') }}
