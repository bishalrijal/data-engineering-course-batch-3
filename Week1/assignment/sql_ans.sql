create database ride_share;

CREATE TABLE rides (
    ride_id          INTEGER       PRIMARY KEY,
    driver_name      VARCHAR(100)          NOT NULL,
    passenger_name   VARCHAR(100)          NOT NULL,
    pickup_city      VARCHAR(100)          NOT NULL,
    dropoff_city     VARCHAR(100)          NOT NULL,
    fare_amount      NUMERIC(10,2) NOT NULL CHECK (fare_amount >= 0),
    ride_distance_km NUMERIC(6,2)  NOT NULL CHECK (ride_distance_km >= 0),
    ride_status      VARCHAR(50)   NOT NULL default 'pending' CHECK (ride_status IN ('no_show', 'completed', 'cancelled')),
    requested_at     TIMESTAMP     NOT NULL,
    completed_at     TIMESTAMP,
    rating           NUMERIC(2,1) CHECK (rating >= 1.0 AND rating <= 5.0),
    payment_method   VARCHAR(50)
);



-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount

select
	ride_id,
	driver_name,
	passenger_name,
	fare_amount
from
	rides r
where
	ride_status = 'completed'
	and lower(pickup_city) like 'kathmandu'
	and lower(dropoff_city) like 'pokhara';


-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending

select
	driver_name,
	passenger_name,
	fare_amount
from
	rides r
order by
	fare_amount desc
limit 5;


-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive


select 
	distinct driver_name
from
	rides r
where 
	driver_name ilike '%shrestha%';

-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides


select 
	count(*) as total_rides,
	count(rating) as rated_rides,
	SUM(case when rating is null then 1 else 0 end) as unrated_rides
from
	rides r;





-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods

SELECT
	ride_id,
	driver_name,
	payment_method
FROM 
	rides r
WHERE 
	payment_method IS NULL
	OR 
	payment_method != 'cash';




-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc

select
	pickup_city,
	count(*) as total_rides,
	sum(fare_amount) as total_revenue ,
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
	driver_name ,
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
	completed_rides desc





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
	ride_count desc






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
	rating
)
values (
    9001,
'Sunita Gurung',
'Rajan Thapa',
'Lalitpur',
'Bhaktapur',
    350,
12.4,
'completed',
'2026-08-04 12:38:00',
'2026-08-04 12:38:00',
null
);

select
	*
from
	rides
where
	ride_id = 9001




-- 9b. UPDATE the rating to 4.8 for ride_id 9001

update
	rides
set
	rating = 4.8
where
	ride_id = 9001

select
	*
from
	rides
where
	ride_id = 9001



-- Q10 — Locking down payment methods (Intermediate · DDL)
-- 10a. ALTER TABLE to restrict payment_method to a fixed set of values

alter table rides
add constraint pay_method_check
check (payment_method is null
or payment_method in ('', 'card', 'cash', 'esewa', 'khalti'))







-- 10b. INSERT using an invalid payment method — note the error you'd expect in a comment


insert into rides (
    ride_id, driver_name, passenger_name, pickup_city, dropoff_city,
    fare_amount, ride_distance_km, ride_status, requested_at, completed_at, payment_method
)
values (
    9002, 'Sunita Gurung', 'Rajan Thapa', 'Lalitpur', 'Bhaktapur',
    350, 12.4, 'completed', now(), now(), 'paypal'
)







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
		rides)




-- Q12 — Each driver's single best ride (Intermediate · Correlated subquery)
-- driver_name, ride_id, fare_amount — one row per driver, their own max fare_amount


select
	driver_name,
	ride_id,
	fare_amount
from
	rides r1
where
	r1.fare_amount = 
	(
	select
		max(fare_amount)
	from
		rides r2
	where
		r1.driver_name = r2.driver_name)






































