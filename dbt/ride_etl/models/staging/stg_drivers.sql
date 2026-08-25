select
    driver_id,
    name,
    status,
    joined_at
from {{ source('raw', 'drivers') }}
