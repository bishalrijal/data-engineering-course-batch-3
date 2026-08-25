-- mirrors the OLTP check constraint trips_surge_multiplier_check (surge >= 1.00)
select *
from {{ ref('fact_trips') }}
where surge_multiplier < 1.00
