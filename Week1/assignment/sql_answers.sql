-- Week 1 SQL Assignment — Nabina Khadka


-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount
SELECT ride_id, driver_name, passenger_name, fare_amount
FROM rides 
WHERE ride_status = 'completed'
AND lower(pickup_city) LIKE 'kathmandu'
AND lower(dropoff_city) LIKE 'pokhara';


-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending
SELECT driver_name, passenger_name, fare_amount
FROM rides
ORDER BY fare_amount DESC
LIMIT 5;


-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive
SELECT * FROM rides
WHERE driver_name ILIKE '%Shrestha%' ;


-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides
SELECT count(*) AS total_rides ,
count(rating) AS rated_rides,
(count(*) - count(rating) ) AS unrated_rides
FROM rides;


-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods
select ride_id, driver_name, payment_method
from rides 
where payment_method != 'cash'
or payment_method is null


-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc
SELECT pickup_city, count(*) AS total_rides , sum(fare_amount) AS total_revenue , round(avg(fare_amount),2) AS avg_fare
FROM rides
GROUP BY pickup_city
ORDER BY total_revenue DESC;


-- Q7 — Drivers who qualify for the loyalty bonus (Intermediate · Aggregation)
-- driver_name, completed_rides — drivers with more than 100 completed rides, sorted desc
SELECT driver_name , count(*) AS completed_rides FROM rides
WHERE ride_status = 'completed'
GROUP BY driver_name
HAVING count(*) > 100
ORDER BY completed_rides desc


-- Q8 — Ride outcomes by status (Intermediate · Aggregation)
-- ride_status, ride_count, avg_distance_km (2 decimals) — sorted by ride_count desc
SELECT ride_status, count(*) AS ride_count, round(avg(ride_distance_km),2) AS avg_distance_km
FROM rides
GROUP BY ride_status
ORDER BY ride_count desc


-- Q9 — A new driver's first ride (Basic–Intermediate · DML)
-- 9a. INSERT the new ride (ride_id 9001, rating NULL)
INSERT INTO rides 
	(ride_id,driver_name,passenger_name,pickup_city,dropoff_city,fare_amount,ride_distance_km,ride_status,requested_at,completed_at,rating,payment_method) VALUES
	 (9001,'Sunita Gurung','Rajan Thapa','Lalitpur','Bhaktapur',350,12.4,'completed','2026-07-30 11:16:55','2026-07-30 18:26:12.96',null,'esewa');;

SELECT * FROM rides WHERE ride_id = 9001

-- 9b. UPDATE the rating to 4.8 for ride_id 9001
UPDATE rides
SET	rating = 4.8 
WHERE ride_id = 9001

SELECT * FROM rides WHERE ride_id = 9001

-- Q10 — Locking down payment methods (Intermediate · DDL)
-- 10a. ALTER TABLE to restrict payment_method to a fixed set of values
ALTER TABLE rides
DROP CONSTRAINT IF EXISTS payment_method_check;

ALTER TABLE rides
ADD CONSTRAINT payment_method_check
CHECK (payment_method is null or payment_method IN ('wallet','card','cash','esewa','khalti'))

--code that runs
ALTER TABLE rides
ADD CONSTRAINT payment_method_check
CHECK (payment_method is null or payment_method IN ('','card','cash','esewa','khalti'))

-- 10b. INSERT using an invalid payment method — note the error you'd expect in a comment
INSERT INTO rides 
	(ride_id,driver_name,passenger_name,pickup_city,dropoff_city,fare_amount,ride_distance_km,ride_status,requested_at,completed_at,rating,payment_method) VALUES
	 (9002,'Sunita Gurung','Rajan Thapa','Lalitpur','Bhaktapur',350,12.4,'completed','2026-07-30 11:16:55','2026-07-30 18:26:12.96',null,'paypal');

-- Error Message : SQL Error [23514]: ERROR: new row for relation "rides" violates check constraint "payment_method_check"
  --Detail: Failing row contains (9002, 'Sunita Gurung','Rajan Thapa','Lalitpur','Bhaktapur',350,12.4,'completed','2026-07-30 11:16:55','2026-07-30 18:26:12.96',null,'paypal');

-- Q11 — Rides priced above the platform average (Intermediate · Subquery)
-- ride_id, driver_name, fare_amount — fare_amount above the average of ALL rides (via subquery)
SELECT ride_id, driver_name, fare_amount FROM rides 
WHERE fare_amount > (SELECT avg(fare_amount) FROM rides)


-- Q12 — Each driver's single best ride (Intermediate · Correlated subquery)
-- driver_name, ride_id, fare_amount — one row per driver, their own max fare_amount
SELECT driver_name, ride_id, fare_amount FROM rides r1
WHERE r1.fare_amount = 
	(SELECT max(fare_amount) FROM rides r2 WHERE r1.driver_name = r2.driver_name)

