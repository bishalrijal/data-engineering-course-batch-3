select
    row_number() over (order by location_id) as location_key,
    location_id,
    city_name,
    state_province,
    country,
    case
        when state_province in ('New York', 'Pennsylvania') then 'Northeast'
        when state_province in ('Illinois', 'Ohio') then 'Midwest'
        when state_province in ('Texas', 'Florida', 'Tennessee') then 'South'
        when state_province in ('California', 'Arizona', 'Colorado', 'Nevada', 'Oregon', 'Washington') then 'West'
        else 'International'
    end as region,
    latitude,
    longitude
from {{ ref('stg_locations') }}
