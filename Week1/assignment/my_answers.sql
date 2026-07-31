-- Week 1 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.


-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount
select
	ride_id,
	driver_name,
	passenger_name,
	fare_amount
from
	rides
where
	pickup_city = 'Kathmandu'
	and dropoff_city = 'Pokhara'
	and ride_status = 'completed';


-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending
select
	driver_name,
	passenger_name,
	fare_amount
from
	rides
order by
	fare_amount desc
limit 5;


-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive
select
	*
from
	rides
where
	driver_name ilike '%Shrestha%';


-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides
select
	count(*) as total_rides,
	count(rating) as rated_rides,
	count(*)- count(rating) as unrated_rides
from
	rides;


-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods
select
	ride_id,
	driver_name,
	payment_method
from
	rides
where
	payment_method != 'cash'
	or payment_method is null;


-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc
select
	pickup_city,
	count(*) as total_rides,
	sum(fare_amount) as total_revenue,
	round(avg(fare_amount), 2) as avg_fare
from
	rides
group by
	pickup_city
order by
	total_revenue desc;


-- Q7 — Drivers who qualify for the loyalty bonus (Intermediate · Aggregation)
-- driver_name, completed_rides — drivers with more than 100 completed rides, sorted desc
select
	driver_name,
	count(*) as completed_rides
from
	rides
where
	ride_status = 'completed'
group by
	driver_name
having
	count(*) > 100
order by
	completed_rides desc;


-- Q8 — Ride outcomes by status (Intermediate · Aggregation)
-- ride_status, ride_count, avg_distance_km (2 decimals) — sorted by ride_count desc
select
	ride_status,
	count(*) as ride_count,
	round(avg(ride_distance_km), 2) as avg_distance_km
from
	rides
group by
	ride_status
order by
	ride_count desc;


-- Q9 — A new driver's first ride (Basic–Intermediate · DML)
-- 9a. INSERT the new ride (ride_id 9001, rating NULL)
insert
	into
	rides (
    ride_id,
	driver_name,
	passenger_name,
	pickup_city,
	dropoff_city,
	fare_amount,
	ride_distance_km,
	ride_status,
	requested_at,
	completed_at,
	rating,
	payment_method
)
values (
    9001, 
    'Sunita Gurung', 
    'Rajan Thapa', 
    'Lalitpur', 
    'Bhaktapur', 
    350.00, 
    12.40, 
    'completed', 
    CURRENT_TIMESTAMP, 
    CURRENT_TIMESTAMP, 
    null, 
    'cash'
);

-- 9b. UPDATE the rating to 4.8 for ride_id 9001
update
	rides
set
	rating = 4.8
where
	ride_id = 9001;

-- Q10 — Locking down payment methods (Intermediate · DDL)
-- 10a. ALTER TABLE to restrict payment_method to a fixed set of values
alter table rides
add constraint chk_payment_method 
check (payment_method in ('cash', 'esewa', 'khalti', 'card', 'wallet'));


-- 10b. INSERT using an invalid payment method — note the error you'd expect in a comment
insert
	into
	rides (
    ride_id,
	driver_name,
	passenger_name,
	pickup_city,
	dropoff_city,
	fare_amount,
	ride_distance_km,
	ride_status,
	requested_at,
	payment_method
)
values (
    9002,
'Test Driver',
'Test Passenger',
'Kathmandu',
'Lalitpur', 
    200.00,
5.0,
'completed',
CURRENT_TIMESTAMP,
'paypal'
);

--Expected Error: ERROR: new row for relation "rides" violates check constraint "chk_payment_method"
--Reasoning: The inserting tuple contains 'paypal' in payment_method attribute which violates the check constraints from question 10a.

-- Q11 — Rides priced above the platform average (Intermediate · Subquery)
-- ride_id, driver_name, fare_amount — fare_amount above the average of ALL rides (via subquery)
select
	ride_id,
	driver_name,
	fare_amount
from
	rides
where
	fare_amount > (
	select
		avg(fare_amount)
	from
		rides
);


-- Q12 — Each driver's single best ride (Intermediate · Correlated subquery)
-- driver_name, ride_id, fare_amount — one row per driver, their own max fare_amount
select
	r.driver_name,
	r.ride_id,
	r.fare_amount
from
	rides r
where
	r.fare_amount = (
	select
		MAX(sub.fare_amount)
	from
		rides sub
	where
		sub.driver_name = r.driver_name
);
