-- Week 1 SQL Assignment — Answers
-- Fill in each query below. See sql_assignment.md for the full scenario text.
-- Rename this file to sql_answers.sql before committing.


-- Q1 — Kathmandu to Pokhara (Basic · DQL)
-- Completed rides from Kathmandu to Pokhara: ride_id, driver_name, passenger_name, fare_amount
select ride_id, driver_name, passenger_name, fare_amount from rides 
where ride_status='completed' and 
pickup_city = 'Kathmandu' and 
dropoff_city = 'Pokhara';



-- Q2 — Top 5 highest fares (Basic · DQL)
-- driver_name, passenger_name, fare_amount — 5 highest fares, descending
select driver_name, passenger_name, fare_amount from rides
order by fare_amount desc limit 5;


-- Q3 — The "Shrestha" complaint (Basic · DQL)
-- Every ride where driver_name contains "shrestha", case-insensitive
select driver_name from rides where driver_name ILIKE '%shrestha%';


-- Q4 — How many rides were never rated? (Basic–Intermediate · NULL)
-- One query returning: total_rides, rated_rides, unrated_rides
select count(*) total_rides, count(rating) rated_rides, total_rides-rated_rides unrated_rides from rides; 


-- Q5 — Every ride that wasn't paid in cash (Intermediate · NULL)
-- ride_id, driver_name, payment_method — not cash, including unrecorded payment methods
select ride_id, driver_name, payment_method from rides where payment_methods!=cash;


-- Q6 — Revenue by pickup city (Intermediate · Aggregation)
-- pickup_city, total_rides, total_revenue, avg_fare (2 decimals) — sorted by total_revenue desc
select pickup_city, count(ride_id) total_rides, sum(fare_amount) total_revenue, round(avg(fare_amount)::numeric,2) avg_fare
from rides GROUP BY pickup_city order BY total_revenue desc;


-- Q7 — Drivers who qualify for the loyalty bonus (Intermediate · Aggregation)
-- driver_name, completed_rides — drivers with more than 100 completed rides, sorted desc
select driver_name, count(ride_status) completed_rides from rides where ride_status = 'completed'
group by driver_name
having count(ride_status)>100  order by completed_rides desc;


-- Q8 — Ride outcomes by status (Intermediate · Aggregation)
-- ride_status, ride_count, avg_distance_km (2 decimals) — sorted by ride_count desc
select ride_status, count(ride_id) ride_count, round(avg(ride_distance_km)::numeric,2) avg_distance_km from rides
group by ride_status order by ride_count desc;



-- Q9 — A new driver's first ride (Basic–Intermediate · DML)
-- 9a. INSERT the new ride (ride_id 9001, rating NULL)
insert into rides values (9001,'lalit joshi','nicole watson', 'kathmandu', 'pokhara', 500, 36, 'completed', '12/24/2024  7:52:57 PM','12/25/2024  8:49:21 PM', NULL, 'esewa');
select * from rides where ride_id=9001;
-- 9b. UPDATE the rating to 4.8 for ride_id 9001
update rides set rating = 4.8 where ride_id = 9001;


-- Q10 — Locking down payment methods (Intermediate · DDL)
-- 10a. ALTER TABLE to restrict payment_method to a fixed set of values
ALTER TABLE rides 
ADD CONSTRAINT chk_payment_method 
CHECK (payment_method IN ('cash', 'esewa', 'khalti', 'card', 'wallet'));

-- 10b. INSERT using an invalid payment method — note the error you'd expect in a comment
insert into rides values (9002,'lalit joshi','nicole watson', 'kathmandu', 'pokhara', 500, 36, 'completed', '12/24/2024  7:52:57 PM','12/25/2024  8:49:21 PM', NULL, 'paypal');


-- Q11 — Rides priced above the platform average (Intermediate · Subquery)
-- ride_id, driver_name, fare_amount — fare_amount above the average of ALL rides (via subquery)
select
    ride_id, 
    driver_name, 
    fare_amount
FROM 
    rides
WHERE 
    fare_amount > (SELECT AVG(fare_amount) FROM rides);



-- Q12 — Each driver's single best ride (Intermediate · Correlated subquery)
-- driver_name, ride_id, fare_amount — one row per driver, their own max fare_amount

select driver_name, ride_id, fare_amount from rides r1
where fare_amount = (
    SELECT MAX(fare_amount)
    FROM rides r2
    where r2.driver_name = r1.driver_name
);