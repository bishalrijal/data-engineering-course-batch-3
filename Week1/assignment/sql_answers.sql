-- Week 1 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.


-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount
SELECT ride_id, driver_name, passenger_name, fare_amount
FROM rides
WHERE ride_status = 'completed'
  AND pickup_city = 'Kathmandu'
  AND dropoff_city = 'Pokhara';


-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending

SELECT driver_name, passenger_name, fare_amount
FROM rides
ORDER BY fare_amount DESC
LIMIT 5;

-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive
SELECT *
FROM rides
WHERE driver_name ILIKE '%shrestha%';


-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides

SELECT 
    COUNT(*) AS total_rides,
    COUNT(rating) AS rated_rides,
    COUNT(*) - COUNT(rating) AS unrated_rides
FROM rides;

-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods
SELECT ride_id, driver_name, payment_method
FROM rides
WHERE payment_method IS DISTINCT FROM 'cash';


-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc
SELECT
    pickup_city,
    COUNT(*) AS total_rides,
    SUM(fare_amount) AS total_revenue,
    ROUND(AVG(fare_amount), 2) AS avg_fare
FROM rides
GROUP BY pickup_city
ORDER BY total_revenue DESC;


-- Q7 — Drivers who qualify for the loyalty bonus (Intermediate · Aggregation)
-- driver_name, completed_rides — drivers with more than 100 completed rides, sorted desc
SELECT
    driver_name,
    COUNT(*) AS completed_rides
FROM rides
WHERE ride_status = 'completed'
GROUP BY driver_name
HAVING COUNT(*) > 100
ORDER BY completed_rides DESC;


-- Q8 — Ride outcomes by status (Intermediate · Aggregation)
-- ride_status, ride_count, avg_distance_km (2 decimals) — sorted by ride_count desc

SELECT
    ride_status,
    COUNT(*) AS ride_count,
    ROUND(AVG(ride_distance_km), 2) AS avg_distance_km
FROM rides
GROUP BY ride_status
ORDER BY ride_count DESC;

-- Q9 — A new driver's first ride (Basic–Intermediate · DML)
-- 9a. INSERT the new ride (ride_id 9001, rating NULL)
INSERT INTO rides (
    ride_id, driver_name, passenger_name, pickup_city, dropoff_city,
    fare_amount, ride_distance_km, ride_status,
    requested_at, completed_at, rating, payment_method
) VALUES (
    9001, 'Sunita Gurung', 'Rajan Thapa', 'Lalitpur', 'Bhaktapur',
    350.00, 12.4, 'completed',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, NULL
);
 

-- 9b. UPDATE the rating to 4.8 for ride_id 9001
UPDATE rides
SET rating = 4.8
WHERE ride_id = 9001;


-- Q10 — Locking down payment methods (Intermediate · DDL)
-- 10a. ALTER TABLE to restrict payment_method to a fixed set of values
ALTER TABLE rides
ADD CONSTRAINT chk_payment_method 
CHECK (payment_method IN ('cash', 'esewa', 'khalti', 'card', 'wallet'));

-- 10b. INSERT using an invalid payment method — note the error you'd expect in a comment
INSERT INTO rides (
    ride_id, driver_name, passenger_name, pickup_city, dropoff_city, 
    fare_amount, ride_distance_km, ride_status, requested_at, payment_method
) VALUES (
    9002, 'Test Driver', 'Test Passenger', 'Kathmandu', 'Lalitpur', 
    200.00, 5.00, 'completed', CURRENT_TIMESTAMP, 'paypal'
);
-- EXPECTED ERROR:
-- ERROR: new row for relation "rides" violates check constraint "chk_payment_method"
-- DETAIL: Failing row contains (9002, Test Driver, Test Passenger, Kathmandu, Lalitpur, 200.00, 5.00, completed, 2026-08-04 20:39:00, null, null, paypal).



-- Q11 — Rides priced above the platform average (Intermediate · Subquery)
-- ride_id, driver_name, fare_amount — fare_amount above the average of ALL rides (via subquery)
SELECT 
    ride_id, 
    driver_name, 
    fare_amount
FROM rides
WHERE fare_amount > (SELECT AVG(fare_amount) FROM rides);



-- Q12 — Each driver's single best ride (Intermediate · Correlated subquery)
-- driver_name, ride_id, fare_amount — one row per driver, their own max fare_amount
SELECT 
    r.driver_name, 
    r.ride_id, 
    r.fare_amount
FROM rides r
WHERE r.fare_amount = (
    SELECT MAX(r2.fare_amount)
    FROM rides r2
    WHERE r2.driver_name = r.driver_name
);
