with trips as (
    select * from {{ ref('stg_trips') }}
),

drivers as (
    select driver_key, driver_id from {{ ref('dim_driver') }}
),

passengers as (
    select passenger_key, passenger_id from {{ ref('dim_passenger') }}
),

locations as (
    select location_key, location_id from {{ ref('dim_location') }}
),

payment_methods as (
    select payment_method_key, payment_method_id from {{ ref('dim_payment_method') }}
),

promo_codes as (
    select promo_code_key, promo_code_id from {{ ref('dim_promo_code') }}
)

select
    row_number() over (order by trips.trip_id) as trip_key,
    trips.trip_id as source_trip_id,

    trips.date_key,
    drivers.driver_key,
    passengers.passenger_key,
    pickup.location_key as pickup_location_key,
    dropoff.location_key as dropoff_location_key,
    payment_methods.payment_method_key,
    promo_codes.promo_code_key,

    trips.base_fare,
    trips.tip_amount,
    trips.discount_amount,
    (trips.base_fare * trips.surge_multiplier) + trips.tip_amount - trips.discount_amount as fare_amount,
    trips.distance_km,
    case
        when trips.status = 'completed'
            then extract(epoch from (trips.completed_at - trips.requested_at)) / 60
    end as duration_minutes,
    1 as trip_count,

    trips.driver_rating,
    trips.passenger_rating,
    trips.surge_multiplier,

    trips.requested_at

from trips
inner join drivers        on trips.driver_id = drivers.driver_id
inner join passengers     on trips.passenger_id = passengers.passenger_id
inner join locations as pickup  on trips.pickup_location_id = pickup.location_id
inner join locations as dropoff on trips.dropoff_location_id = dropoff.location_id
left join payment_methods on trips.payment_method_id is not distinct from payment_methods.payment_method_id
left join promo_codes     on trips.promo_code_id is not distinct from promo_codes.promo_code_id
