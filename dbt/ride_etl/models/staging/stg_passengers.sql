select
    passenger_id,
    name,
    status,
    created_at
from {{ source('raw', 'passengers') }}
