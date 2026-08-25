with payment_methods as (
    select payment_method_id, name, type, is_active
    from {{ ref('stg_payment_methods') }}

    union all

    select null, 'Unknown', null, null
)

select
    row_number() over (order by payment_method_id nulls last) as payment_method_key,
    payment_method_id,
    name,
    type,
    is_active
from payment_methods
