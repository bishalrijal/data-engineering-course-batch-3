select
    row_number() over (order by driver_id) as driver_key,
    driver_id,
    name,
    status,
    joined_at,
    case
        when joined_at >= now() - interval '6 months' then '0-6 months'
        when joined_at >= now() - interval '1 year'   then '6-12 months'
        when joined_at >= now() - interval '2 years'  then '1-2 years'
        else '2+ years'
    end as tenure_bucket
from {{ ref('stg_drivers') }}
