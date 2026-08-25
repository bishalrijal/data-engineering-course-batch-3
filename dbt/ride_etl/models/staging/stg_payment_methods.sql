select
    payment_method_id,
    name,
    type,
    is_active
from {{ source('raw', 'payment_methods') }}
