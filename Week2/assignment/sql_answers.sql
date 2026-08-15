-- Week 2 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.


-- Q1 — Standardizing driver names from the raw feed (Basic · String functions)
-- Distinct, cleaned driver_name from rides — one column: clean_driver_name
SELECT DISTINCT
    INITCAP(TRIM(REGEXP_REPLACE(driver_name, '\s+', ' ', 'g'))) AS clean_driver_name
FROM rides
ORDER BY clean_driver_name;

-- Q2 — Every payment method actually in use (Basic · String functions)
-- Distinct, lowercased payment_method from rides, sorted alphabetically
SELECT DISTINCT LOWER(payment_method) AS payment_method
FROM rides
ORDER BY payment_method;

-- Q3 — A readable log of every completed trip (Basic · Joins)
-- driver_name, passenger_name, pickup_city, dropoff_city, fare_amount, requested_at
-- Join locations twice (pickup + dropoff) with separate aliases
SELECT
    d.name AS driver_name,
    p.name AS passenger_name,
    pickup.city_name AS pickup_city,
    dropoff.city_name AS dropoff_city,
    t.fare_amount,
    t.requested_at
FROM trips t
JOIN drivers d
    ON t.driver_id = d.driver_id
JOIN passengers p
    ON t.passenger_id = p.passenger_id
JOIN locations pickup
    ON t.pickup_location_id = pickup.location_id
JOIN locations dropoff
    ON t.dropoff_location_id = dropoff.location_id
WHERE t.status = 'completed';

-- Q4 — Drivers who have never driven a single trip (Basic–Intermediate · Joins)
-- driver_name — drivers with zero rows in trips at all
-- Comment: why can't INNER JOIN answer this?
SELECT d.name AS driver_name
FROM drivers d
LEFT JOIN trips t
    ON d.driver_id = t.driver_id
WHERE t.trip_id IS NULL;

-- Q5 — Payment methods nobody has ever used (Intermediate · Joins)
-- payment_method_id, name — payment methods with zero trips
-- Comment: which join type / FROM table if written the other way around?
SELECT pm.payment_method_id, pm.name
FROM payment_methods pm
LEFT JOIN trips t
    ON pm.payment_method_id = t.payment_method_id
WHERE t.trip_id IS NULL;

-- Q6 — Numbering each driver's trips in order (Basic–Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, trip_number (ROW_NUMBER per driver)
SELECT d.name AS driver_name, t.requested_at, t.fare_amount,
    ROW_NUMBER() OVER (
        PARTITION BY t.driver_id
        ORDER BY t.requested_at
    ) AS trip_number
FROM trips t
JOIN drivers d
    ON t.driver_id = d.driver_id
ORDER BY d.name, trip_number;

-- Q7 — Each driver's running earnings (Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, running_total (cumulative SUM per driver)
SELECT d.name AS driver_name, t.requested_at, t.fare_amount,
    SUM(t.fare_amount) OVER (
        PARTITION BY t.driver_id
        ORDER BY t.requested_at
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total
FROM trips t
JOIN drivers d
    ON t.driver_id = d.driver_id
ORDER BY d.name, t.requested_at;

-- Q8 — Each driver's single highest-fare trip, without a subquery (Intermediate · Window functions)
-- driver_name, trip_id, fare_amount — one row per driver, via RANK()/ROW_NUMBER() + CTE
WITH ranked_trips AS (
    SELECT d.name AS driver_name, t.trip_id, t.fare_amount,
        ROW_NUMBER() OVER (
            PARTITION BY t.driver_id
            ORDER BY t.fare_amount DESC, t.trip_id
        ) AS rn
    FROM trips t
    JOIN drivers d
        ON t.driver_id = d.driver_id
)
SELECT driver_name, trip_id, fare_amount
FROM ranked_trips
WHERE rn = 1
ORDER BY driver_name;

-- Q9 — Driver performance scorecard (Intermediate · Conditional aggregation)
-- driver_name, total_trips, completed_trips, cancelled_trips, cancellation_rate, avg_rating
-- Q9 — Driver performance scorecard

SELECT d.name AS driver_name,
    COUNT(t.trip_id) AS total_trips,
    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) AS completed_trips,
    COUNT(CASE WHEN t.status = 'cancelled' THEN 1 END) AS cancelled_trips,
    ROUND(
        COUNT(CASE WHEN t.status = 'cancelled' THEN 1 END) * 100.0
        / NULLIF(COUNT(t.trip_id), 0),
        2
    ) AS cancellation_rate,
    ROUND(AVG(t.rating), 2) AS avg_rating
FROM drivers d
LEFT JOIN trips t
    ON d.driver_id = t.driver_id
GROUP BY d.name
ORDER BY d.name;

-- Q10 — Onboarding a new driver atomically (Intermediate · Transactions)
-- BEGIN; INSERT driver; 3x INSERT trip; COMMIT;
-- Comment: what would trigger a rollback, and what happens to the driver row then?
BEGIN;

INSERT INTO drivers (name)
VALUES ('Sunita Gurung');

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
VALUES (
    (SELECT driver_id FROM drivers WHERE name = 'Sunita Gurung'),
    1,
    1,
    2,
    300.00,
    5.00,
    'completed',
    '2026-08-15 09:00:00',
    '2026-08-15 09:20:00',
    5.0,
    1
);

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
VALUES (
    (SELECT driver_id FROM drivers WHERE name = 'Sunita Gurung'),
    2,
    2,
    3,
    450.00,
    7.00,
    'completed',
    '2026-08-15 10:00:00',
    '2026-08-15 10:30:00',
    4.5,
    1
);

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
VALUES (
    (SELECT driver_id FROM drivers WHERE name = 'Sunita Gurung'),
    3,
    3,
    4,
    250.00,
    4.00,
    'completed',
    '2026-08-15 11:00:00',
    '2026-08-15 11:20:00',
    4.0,
    1
);

COMMIT;

-- Q11 — A saved view for the ops dashboard (Intermediate · Views)
-- 11a. CREATE VIEW driver_cancellation_summary AS ...
CREATE VIEW driver_cancellation_summary AS
SELECT d.name AS driver_name,
    COUNT(t.trip_id) AS total_trips,
    COUNT(CASE WHEN t.status = 'cancelled' THEN 1 END) AS cancelled_trips,
    ROUND(
        COUNT(CASE WHEN t.status = 'cancelled' THEN 1 END) * 100.0
        / NULLIF(COUNT(t.trip_id), 0),
        2
    ) AS cancellation_rate
FROM drivers d
LEFT JOIN trips t
    ON d.driver_id = t.driver_id
GROUP BY d.name;

-- 11b. SELECT from the view: drivers with cancellation_rate above 20%
SELECT *
FROM driver_cancellation_summary;

SELECT *
FROM driver_cancellation_summary
WHERE cancellation_rate > 20;

-- Q12 — Speeding up a slow driver lookup (Intermediate · Indexing — beyond the pre-reads)
-- 12a. EXPLAIN ANALYZE before the index — note scan type + execution time in a comment
EXPLAIN ANALYZE
SELECT *
FROM trips
WHERE driver_id = 17;

-- 12b. CREATE INDEX
CREATE INDEX idx_trips_driver_id
ON trips(driver_id);

-- 12c. EXPLAIN ANALYZE after the index — note what changed in a comment
EXPLAIN ANALYZE
SELECT *
FROM trips
WHERE driver_id = 17;
--changes seq scan to index scan by idx_trips_driver_id
--execution time: 0.582ms to 0.095ms
