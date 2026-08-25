select
    promo_code_id,
    code,
    discount_type,
    discount_value,
    is_active
from {{ source('raw', 'promo_codes') }}
