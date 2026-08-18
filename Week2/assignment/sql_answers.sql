-- Week 2 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.


-- Q1 — Standardizing driver names from the raw feed (Basic · String functions)
-- Distinct, cleaned driver_name from rides — one column: clean_driver_name
SELECT DISTINCT 
initcap(
TRIM(
regexp_replace(driver_name,'\s+',' ','g')
))
AS clean_driver_name
FROM rides r 
ORDER BY clean_driver_name;


-- Q2 — Every payment method actually in use (Basic · String functions)
-- Distinct, lowercased payment_method from rides, sorted alphabetically
SELECT DISTINCT (
lower(TRIM(payment_method))
) AS payment_method
FROM rides 
WHERE payment_method IS NOT NULL
ORDER BY payment_method;


-- Q3 — A readable log of every completed trip (Basic · Joins)
-- driver_name, passenger_name, pickup_city, dropoff_city, fare_amount, requested_at
-- Join locations twice (pickup + dropoff) with separate aliases
SELECT
d.name AS driver_name,
p.name AS  passenger_name,
pck.city_name AS  pickup_city,
dst.city_name AS  dropoff_city,
t.fare_amount,
t.requested_at
FROM trips t
INNER JOIN drivers d
ON t.driver_id=d.driver_id
INNER JOIN passengers p
ON t.passenger_id=p.passenger_id
INNER JOIN locations pck
ON t.pickup_location_id=pck.location_id
INNER JOIN locations dst
ON t.dropoff_location_id=dst.location_id
WHERE t.status='completed';



-- Q4 — Drivers who have never driven a single trip (Basic–Intermediate · Joins)
-- driver_name — drivers with zero rows in trips at all
-- Comment: why can't INNER JOIN answer this?
SELECT
d.name AS driver_name
FROM drivers d 
LEFT JOIN trips t
ON d.driver_id=t.driver_id 
WHERE t.trip_id IS NULL;

---Here we cant use inner join because it will remove drivers who dont have matching rows in trip



-- Q5 — Payment methods nobody has ever used (Intermediate · Joins)
-- payment_method_id, name — payment methods with zero trips
-- Comment: which join type / FROM table if written the other way around?
SELECT 
pm.payment_method_id,
pm.name
FROM payment_methods pm 
LEFT JOIN trips t
ON pm.payment_method_id=t.payment_method_id 
WHERE t.trip_id IS NULL;
  ---left join is used as payment_method as left table because we want to keep all payment methods even the ones with no trips
---if the from table was trips right join would be used


-- Q6 — Numbering each driver's trips in order (Basic–Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, trip_number (ROW_NUMBER per driver)
SELECT d.name AS driver_name,
t.requested_at,
t.fare_amount,
row_number() 
over(
PARTITION BY t.driver_id
ORDER BY t.requested_at
) AS trip_number
FROM trips t
INNER JOIN drivers d
ON t.driver_id = d.driver_id
ORDER BY d.name,
trip_number;







-- Q7 — Each driver's running earnings (Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, running_total (cumulative SUM per driver)
SELECT d.name AS driver_name,
t.requested_at,
t.fare_amount,
SUM(t.fare_amount) OVER (
PARTITION BY t.driver_id
ORDER BY t.requested_at
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS running_total
FROM trips t
JOIN drivers d
ON t.driver_id = d.driver_id
ORDER BY driver_name, t.requested_at;





-- Q8 — Each driver's single highest-fare trip, without a subquery (Intermediate · Window functions)
-- driver_name, trip_id, fare_amount — one row per driver, via RANK()/ROW_NUMBER() + CTE
WITH ranked_trips AS (
SELECT
d.name AS driver_name,
t.trip_id,
t.fare_amount,
ROW_NUMBER() OVER (
PARTITION BY t.driver_id
ORDER BY t.fare_amount DESC, t.trip_id
) AS rn
FROM trips t
JOIN drivers d
ON t.driver_id = d.driver_id
)
SELECT
driver_name,
trip_id,
fare_amount
FROM ranked_trips
WHERE rn = 1;

-- Q9 — Driver performance scorecard (Intermediate · Conditional aggregation)
-- driver_name, total_trips, completed_trips, cancelled_trips, cancellation_rate, avg_rating
WITH ranked_trips AS (
SELECT
d.name AS driver_name,
t.trip_id,
t.fare_amount,
ROW_NUMBER() OVER (
PARTITION BY t.driver_id
ORDER BY t.fare_amount DESC, t.trip_id
) AS rn
FROM trips t
JOIN drivers d
ON t.driver_id = d.driver_id
)
SELECT
driver_name,
trip_id,
fare_amount
FROM ranked_trips
WHERE rn = 1;



-- Q10 — Onboarding a new driver atomically (Intermediate · Transactions)
-- BEGIN; INSERT driver; 3x INSERT trip; COMMIT;
-- Comment: what would trigger a rollback, and what happens to the driver row then?

BEGIN;

INSERT INTO drivers (name)
VALUES ('Rishika Baral')
RETURNING driver_id;



INSERT INTO trips (
    driver_id,
    passenger_id,
    pickup_location_id,
    dropoff_location_id,
    fare_amount,
    distance_km,
    status,
    requested_at,
    completed_at,
    rating,
    payment_method_id
)
VALUES
    (20, 7, 6, 9, 450.00, 5.20, 'completed',
     '2026-08-18 10:00:00', '2026-08-18 10:25:00', 5.0, 5),

    (20, 8, 12, 7, 600.00, 7.50, 'completed',
     '2026-08-18 11:00:00', '2026-08-18 11:30:00', 4.5, 2),

    (20, 6, 7, 10, 350.00, 4.10, 'failed',
     '2026-08-18 12:00:00', NULL, NULL, 4);

ROLLBACK ;

SELECT *
FROM drivers
WHERE driver_id = 20;


--here the failed value for status causes the transaction to abort and rollback restors the previous form
--- Since there is a error in transaction the rollback restores the trips table to as it is instead of updating it



-- Q11 — A saved view for the ops dashboard (Intermediate · Views)
-- 11a. CREATE VIEW driver_cancellation_summary AS ...


CREATE VIEW driver_cancellation_summary AS
SELECT
d.name AS driver_name,
COUNT(t.trip_id) AS total_trips,
COUNT(t.trip_id) FILTER (WHERE t.status = 'cancelled') AS cancelled_trips,
ROUND(
100.0 * COUNT(t.trip_id) FILTER (WHERE t.status = 'cancelled')
/ NULLIF(COUNT(t.trip_id), 0),
2
) AS cancellation_rate
FROM drivers d
LEFT JOIN trips t
ON d.driver_id = t.driver_id
GROUP BY d.driver_id, d.name;


SELECT *
FROM driver_cancellation_summary;

-- 11b. SELECT from the view: drivers with cancellation_rate above 20%

SELECT *
FROM driver_cancellation_summary
WHERE cancellation_rate > 20;





-- Q12 — Speeding up a slow driver lookup (Intermediate · Indexing — beyond the pre-reads)
-- 12a. EXPLAIN ANALYZE before the index — note scan type + execution time in a comment
DROP INDEX IF EXISTS idx_trips_driver_status;
DROP INDEX IF EXISTS idx_trips_driver_id;


EXPLAIN ANALYZE
SELECT *
FROM trips
WHERE driver_id = 10;


---Seq Scan on trips  (cost=0.00..127.51 rows=490 width=67) (actual time=0.053..0.518 rows=490.00 loops=1)
--Execution Time: 0.564 ms


-- 12b. CREATE INDEX


CREATE INDEX idx_trips_driver_id
ON trips(driver_id);

-- 12c. EXPLAIN ANALYZE after the index — note what changed in a comment

EXPLAIN ANALYZE
SELECT *
FROM trips
WHERE driver_id = 10;


--Bitmap Heap Scan on trips  (cost=8.08..79.20 rows=490 width=67) (actual time=0.083..0.214 rows=490.00 loops=1)
--  
--  ->  Bitmap Index Scan on idx_trips_driver_id  (cost=0.00..7.96 rows=490 width=0) (actual time=0.060..0.060 rows=490.00 loops=1)
--        
--Execution Time: 0.252 ms



---BEFORE index seq sacn and execution time 0.544ms
--After index Bitmap Heap Scan on trips, Bitmap Index Scan on idx_trips_driver_id    and execution time 0.252
-- we can clearly tell that execution time was faster afetr index

