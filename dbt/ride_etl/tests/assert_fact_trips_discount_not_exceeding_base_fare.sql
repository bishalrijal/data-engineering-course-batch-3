-- mirrors the OLTP check constraint chk_discount_not_exceed_base — guards
-- against the rule silently breaking somewhere in the raw -> staging -> mart chain
select *
from {{ ref('fact_trips') }}
where discount_amount > base_fare
