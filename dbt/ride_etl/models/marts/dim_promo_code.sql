with promo_codes as (
    select promo_code_id, code, discount_type, discount_value, is_active
    from {{ ref('stg_promo_codes') }}

    union all

    select null, 'No Promo', null, null, null
)

select
    row_number() over (order by promo_code_id nulls last) as promo_code_key,
    promo_code_id,
    code,
    discount_type,
    discount_value,
    is_active
from promo_codes
