-- Week 2 SQL Assignment — Nabina Khadka


-- Q1 — Standardizing driver names from the raw feed (Basic · String functions)
-- Distinct, cleaned driver_name from rides — one column: clean_driver_name
select distinct r.driver_name as cleaned_driver_name
from rides r 
where r.driver_name is not null and trim(r.driver_name) <> '' -- to remove null values and extra spaces
order by cleaned_driver_name 


-- Q2 — Every payment method actually in use (Basic · String functions)
-- Distinct, lowercased payment_method from rides, sorted alphabetically
select distinct LOWER(payment_method) as payment_method
from rides r
where r.payment_method is not null and trim(payment_method) != ''	-- to remove null values and extra spaces
order by payment_method 


-- Q3 — A readable log of every completed trip (Basic · Joins)
-- driver_name, passenger_name, pickup_city, dropoff_city, fare_amount, requested_at
-- Join locations twice (pickup + dropoff) with separate aliases
select r.driver_name, r.passenger_name, pck.city_name as pickup_city , dst.city_name as dropoff_city , r.fare_amount, r.requested_at
from rides r 
inner join locations pck 
on r.pickup_city = pck.city_name 
inner join locations dst
on r.dropoff_city = dst.city_name 
where r.ride_status = 'completed'
-- order by r.driver_name  -- sorts alphabetically


-- Q4 — Drivers who have never driven a single trip (Basic–Intermediate · Joins)
-- driver_name — drivers with zero rows in trips at all
-- Comment: why can't INNER JOIN answer this?
select d.name as driver_name 
from drivers d
left join trips t
on d.driver_id  = t.driver_id  
where t.driver_id is null
order by d.name 

-- Inner Join prints all records of driver name in both table, regardless of their trip count. Using left join, we can extract driver name from drivers table 
-- who have no matching records of trips in trip table. In other words, drivers who do not have any trip do not have matching records in trips table.


-- Q5 — Payment methods nobody has ever used (Intermediate · Joins)
-- payment_method_id, name — payment methods with zero trips
-- Comment: which join type / FROM table if written the other way around?
select pm.payment_method_id, pm.name 
from payment_methods pm 
left join trips t 
on pm.payment_method_id = t.payment_method_id 
where t.trip_id is null

-- For the other way around, right join can be used on payment_methods table and trips table.


-- Q6 — Numbering each driver's trips in order (Basic–Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, trip_number (ROW_NUMBER per driver)
select d.name as driver_name, t.requested_at, t.fare_amount ,
row_number() over (partition by t.driver_id 
				   order by t.requested_at) as trip_number
from trips t 
join drivers d
on d.driver_id = t.driver_id
order by driver_name ,trip_number 


-- Q7 — Each driver's running earnings (Intermediate · Window functions)
-- driver_name, requested_at, fare_amount, running_total (cumulative SUM per driver)
select d.name as driver_name, t.requested_at, t.fare_amount ,
sum(t.fare_amount) over (partition by t.driver_id 
					order by t.requested_at) as running_total
from trips t
join drivers d
on d.driver_id = t.driver_id 
order by driver_name


-- Q8 — Each driver's single highest-fare trip, without a subquery (Intermediate · Window functions)
-- driver_name, trip_id, fare_amount — one row per driver, via RANK()/ROW_NUMBER() + CTE
with rank_trip as (
	select d.name as driver_name , t.trip_id , t.fare_amount ,
	row_number() over (partition by t.driver_id 
						order by t.fare_amount desc) as total_rank -- highest fare is at the beginning
	from trips t
	join drivers d 
	on d.driver_id = t.driver_id
)
-- print only the highest fare
select rt.driver_name , rt.trip_id , rt.fare_amount 
from rank_trip rt
where rt.total_rank=1 --rank 1 represents the highest fare
order by driver_name


-- Q9 — Driver performance scorecard (Intermediate · Conditional aggregation)
-- driver_name, total_trips, completed_trips, cancelled_trips, cancellation_rate, avg_rating
select d.name as driver_name , count(t.trip_id) as total_trips,
count(*) filter( where t.status ='completed' ) as completed_trips,
count(*) filter( where t.status ='cancelled' ) as cancelled_trips ,
round( 100 * count(*) filter(where t.status ='cancelled') / nullif (count(t.trip_id),0),2) as cancellation_rate,
round (avg(t.rating) filter(where t.rating is not null),2) as average_rating
from drivers d
left join trips t
on t.driver_id = d.driver_id
group by driver_name


-- Q10 — Onboarding a new driver atomically (Intermediate · Transactions)
-- BEGIN; INSERT driver; 3x INSERT trip; COMMIT;
-- Comment: what would trigger a rollback, and what happens to the driver row then?
begin;
	-- add a new driver: Sunita Gurung
	insert into drivers(name) values ('Sunita Gurung');
	
	-- add 3x trip details
	insert into trips (driver_id, passenger_id, pickup_location_id,
                     dropoff_location_id, fare_amount, distance_km,
                     status, requested_at)
 	values (1, 1, 1, 2, 123.00, 8.5, 'completed', NOW());
	
	insert into trips (driver_id, passenger_id, pickup_location_id,
                     dropoff_location_id, fare_amount, distance_km,
                     status, requested_at)
  	values (1, 1, 1, 2, 350.00, 8.5, 'cancelled', NOW());
	
	insert into trips (driver_id, passenger_id, pickup_location_id,
                     dropoff_location_id, fare_amount, distance_km,
                     status, requested_at)
 	 values (1, 1, 1, 2, 250.00, 8.5, 'completed', NOW());
	
commit;

-- Insertion of any invalid data triggers a rollback.
-- When a rollback occurs, the database goes back to its previous state i.e. none of the inserts gets saved. 


-- Q11 — A saved view for the ops dashboard (Intermediate · Views)
-- 11a. CREATE VIEW driver_cancellation_summary AS ...
create view driver_cancellation_summary as 
	select d.name as driver_name , count(t.trip_id) as total_trips,
	count(*) filter( where t.status ='completed' ) as completed_trips,
	count(*) filter( where t.status ='cancelled' ) as cancelled_trips ,
	round( 100 * count(*) filter(where t.status ='cancelled') / nullif (count(t.trip_id),0),2) as cancellation_rate,
	round (avg(t.rating) filter(where t.rating is not null),2) as average_rating
	from drivers d
	left join trips t
	on t.driver_id = d.driver_id
	group by driver_name
	
-- 11b. SELECT from the view: drivers with cancellation_rate above 20%

select * from driver_cancellation_summary
where cancellation_rate > 20
order by driver_name 


-- Q12 — Speeding up a slow driver lookup (Intermediate · Indexing — beyond the pre-reads)
-- 12a. EXPLAIN ANALYZE before the index — note scan type + execution time in a comment
explain analyze 
select * from drivers d 
where d.driver_id = 14

-- Index Scan using drivers_pkey on drivers d  (cost=0.15..8.17 rows=1 width=222) (actual time=0.051..0.053 rows=1 loops=1)
-- Index Cond: (driver_id = 14)
-- Planning Time: 0.079 ms
-- Execution Time: 0.068 ms

-- 12b. CREATE INDEX
create index index_drivers
on drivers(driver_id)

--Seq Scan on drivers d  (cost=0.00..1.19 rows=1 width=222) (actual time=0.024..0.025 rows=1 loops=1)
--  Filter: (driver_id = 14)
--  Rows Removed by Filter: 14
--Planning Time: 0.835 ms
--Execution Time: 0.046 ms


-- 12c. EXPLAIN ANALYZE after the index — note what changed in a comment
-- Before Indexing, the query ran through all the data, row by row. Indexing helped reduce the execution time by jumping into the desired row, here: the row
-- with the driver id 14. 
