select
    location_id,
    city_name,
    state_province,
    country,
    latitude,
    longitude
from {{ source('raw', 'locations') }}
