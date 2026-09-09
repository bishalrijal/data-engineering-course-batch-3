#!/usr/bin/env python3
"""
sample_data_loader.py
─────────────────────
Generates and loads sample data into the normalized ride-sharing schema.

  Volumes generated:
    locations             25
    payment_methods        7
    promo_codes           10
    drivers               25  (+1 license each)
    vehicles              30  (+assignments)
    passengers            45
    trips             10 000  (≈80% completed · 15% cancelled · 5% no_show)
    trip_cancellations  ~1 500

  Requirements:
    pip install -r requirements.txt
"""

import os
import random
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
from dotenv import load_dotenv

load_dotenv()
# ─────────────────────────────────────────────────────────────────────────────
# CONFIG  ← update before running
# ─────────────────────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":    os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", 5434),
    "dbname":   os.getenv("DB_NAME", "ride_prod"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

SEED         = 42
N_DRIVERS    = 25
N_PASSENGERS = 45
N_TRIPS      = 10_000
N_VEHICLES   = 30

random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

START_DATE = datetime(2023, 1, 1)
END_DATE   = datetime(2026, 6, 30)


# ─────────────────────────────────────────────────────────────────────────────
# REFERENCE DATA
# ─────────────────────────────────────────────────────────────────────────────

CITIES = [
    # (city_name, state_province, country, latitude, longitude)
    ("New York",      "New York",      "USA",        40.7128,  -74.0060),
    ("Los Angeles",   "California",    "USA",        34.0522, -118.2437),
    ("Chicago",       "Illinois",      "USA",        41.8781,  -87.6298),
    ("Houston",       "Texas",         "USA",        29.7604,  -95.3698),
    ("Phoenix",       "Arizona",       "USA",        33.4484, -112.0740),
    ("Philadelphia",  "Pennsylvania",  "USA",        39.9526,  -75.1652),
    ("San Antonio",   "Texas",         "USA",        29.4241,  -98.4936),
    ("San Diego",     "California",    "USA",        32.7157, -117.1611),
    ("Dallas",        "Texas",         "USA",        32.7767,  -96.7970),
    ("San Jose",      "California",    "USA",        37.3382, -121.8863),
    ("Austin",        "Texas",         "USA",        30.2672,  -97.7431),
    ("Jacksonville",  "Florida",       "USA",        30.3322,  -81.6557),
    ("San Francisco", "California",    "USA",        37.7749, -122.4194),
    ("Columbus",      "Ohio",          "USA",        39.9612,  -82.9988),
    ("Seattle",       "Washington",    "USA",        47.6062, -122.3321),
    ("Denver",        "Colorado",      "USA",        39.7392, -104.9903),
    ("Nashville",     "Tennessee",     "USA",        36.1627,  -86.7816),
    ("Las Vegas",     "Nevada",        "USA",        36.1699, -115.1398),
    ("Portland",      "Oregon",        "USA",        45.5051, -122.6750),
    ("Miami",         "Florida",       "USA",        25.7617,  -80.1918),
    ("Toronto",       "Ontario",       "Canada",     43.6532,  -79.3832),
    ("Vancouver",     "BC",            "Canada",     49.2827, -123.1207),
    ("London",        "England",       "UK",         51.5074,   -0.1278),
    ("Sydney",        "NSW",           "Australia",  -33.8688, 151.2093),
    ("Melbourne",     "Victoria",      "Australia",  -37.8136, 144.9631),
]

PAYMENT_METHODS = [
    # (name, type)
    ("Cash",        "cash"),
    ("Credit Card", "card"),
    ("Debit Card",  "card"),
    ("PayPal",      "wallet"),
    ("Apple Pay",   "wallet"),
    ("Google Pay",  "wallet"),
    ("Voucher",     "voucher"),
]

VEHICLE_CATALOG = [
    # (make, model, category)
    ("Toyota",    "Camry",      "economy"),
    ("Toyota",    "Corolla",    "economy"),
    ("Toyota",    "Highlander", "xl"),
    ("Honda",     "Civic",      "economy"),
    ("Honda",     "Accord",     "comfort"),
    ("Honda",     "Pilot",      "xl"),
    ("Ford",      "Fusion",     "comfort"),
    ("Ford",      "Explorer",   "xl"),
    ("Chevrolet", "Malibu",     "comfort"),
    ("Tesla",     "Model 3",    "luxury"),
    ("Tesla",     "Model S",    "luxury"),
    ("BMW",       "5 Series",   "luxury"),
    ("Mercedes",  "E-Class",    "luxury"),
    ("Hyundai",   "Sonata",     "economy"),
    ("Nissan",    "Altima",     "economy"),
]

COLORS = ["White", "Black", "Silver", "Gray", "Blue", "Red", "Green", "Gold"]

# (code, discount_type, discount_value, use_probability_per_trip)
PROMO_CATALOG = [
    ("WELCOME10", "percent", 10.00, 0.25),
    ("SAVE20",    "percent", 20.00, 0.10),
    ("FLAT5",     "flat",     5.00, 0.20),
    ("FLAT10",    "flat",    10.00, 0.10),
    ("SUMMER15",  "percent", 15.00, 0.10),
    ("HOLIDAY25", "percent", 25.00, 0.05),
    ("NEWUSER",   "percent", 30.00, 0.05),
    ("WEEKDAY5",  "flat",     5.00, 0.15),
    ("AIRPORT10", "flat",    10.00, 0.10),
    ("VIP20",     "percent", 20.00, 0.05),
]

CANCEL_REASONS = [
    "Driver too far away",
    "Found alternative transport",
    "Entered wrong location",
    "Changed plans",
    "Wait time too long",
    "App issue",
    "Price too high",
    "Emergency",
]

# ── weighted distribution constants ──────────────────────────────────────────

TRIP_STATUSES    = ["completed", "cancelled", "no_show"]
TRIP_WEIGHTS     = [0.80,        0.15,        0.05]

DRIVER_STATUSES  = ["active", "inactive", "suspended"]
DRIVER_WEIGHTS   = [85,       10,         5]

PASS_STATUSES    = ["active", "inactive", "banned"]
PASS_WEIGHTS     = [90,       8,          2]

SURGE_VALUES     = [1.00, 1.25, 1.50, 1.75, 2.00, 2.50]
SURGE_WEIGHTS    = [60,   15,   10,   7,    5,    3]

DR_RATING_VALS   = [1.0, 2.0, 3.0, 4.0, 4.5, 5.0]
DR_RATING_WTS    = [1,   2,   5,   20,  30,  42]

PR_RATING_VALS   = [1.0, 2.0, 3.0, 4.0, 4.5, 5.0]
PR_RATING_WTS    = [1,   1,   4,   15,  30,  49]

CANCEL_BY        = ["driver", "passenger", "system"]
CANCEL_BY_WTS    = [40,       45,          15]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def rand_dt(start: datetime = START_DATE, end: datetime = END_DATE) -> datetime:
    """Return a random datetime between start and end."""
    diff = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, diff))


def rand_plate() -> str:
    """Generate a random licence plate like ABC-1234."""
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))
    digits  = "".join(random.choices("0123456789", k=4))
    return f"{letters}-{digits}"


# ─────────────────────────────────────────────────────────────────────────────
# INSERT FUNCTIONS  (each returns IDs or metadata needed by later tables)
# ─────────────────────────────────────────────────────────────────────────────

def insert_locations(cur) -> list[int]:
    rows = [(city, state, country, lat, lon) for city, state, country, lat, lon in CITIES]
    result = execute_values(
        cur,
        """INSERT INTO locations (city_name, state_province, country, latitude, longitude)
           VALUES %s RETURNING location_id""",
        rows, fetch=True,
    )
    return [r[0] for r in result]


def insert_payment_methods(cur) -> list[int]:
    result = execute_values(
        cur,
        "INSERT INTO payment_methods (name, type) VALUES %s RETURNING payment_method_id",
        PAYMENT_METHODS, fetch=True,
    )
    return [r[0] for r in result]


def insert_promo_codes(cur) -> list[dict]:
    """Returns list of dicts: {id, type, value, prob} for use in trip generation."""
    rows = []
    for code, dtype, val, _ in PROMO_CATALOG:
        valid_from  = rand_dt(START_DATE - timedelta(days=60), START_DATE + timedelta(days=60))
        valid_until = valid_from + timedelta(days=random.randint(90, 365))
        rows.append((code, dtype, val, valid_from, valid_until, random.randint(200, 5000), True))

    result = execute_values(
        cur,
        """INSERT INTO promo_codes
               (code, discount_type, discount_value, valid_from, valid_until, max_uses, is_active)
           VALUES %s RETURNING promo_code_id""",
        rows, fetch=True,
    )
    ids = [r[0] for r in result]
    return [
        {"id": ids[i], "type": PROMO_CATALOG[i][1], "value": PROMO_CATALOG[i][2], "prob": PROMO_CATALOG[i][3]}
        for i in range(len(ids))
    ]


def insert_drivers(cur) -> list[int]:
    rows = [
        (
            fake.name(),
            fake.unique.email(),
            fake.unique.numerify("+1-###-###-####"),
            random.choices(DRIVER_STATUSES, DRIVER_WEIGHTS)[0],
            rand_dt(START_DATE - timedelta(days=730), START_DATE),
        )
        for _ in range(N_DRIVERS)
    ]
    result = execute_values(
        cur,
        "INSERT INTO drivers (name, email, phone_number, status, joined_at) VALUES %s RETURNING driver_id",
        rows, fetch=True,
    )
    return [r[0] for r in result]


def insert_driver_licenses(cur, driver_ids: list[int]) -> None:
    """One current licence per driver (satisfies unique partial index on is_current=TRUE)."""
    rows = []
    for did in driver_ids:
        issued = rand_dt(datetime(2015, 1, 1), datetime(2021, 12, 31))
        expiry = issued + timedelta(days=random.choice([4, 5, 6, 8]) * 365)
        rows.append((
            did,
            fake.bothify("??######").upper(),   # e.g. AB123456
            issued.date(),
            expiry.date(),
            True,                               # is_current = TRUE
        ))
    execute_values(
        cur,
        """INSERT INTO driver_licenses (driver_id, license_number, issued_date, expiry_date, is_current)
           VALUES %s""",
        rows,
    )


def insert_vehicles(cur) -> list[int]:
    plates: set[str] = set()
    rows = []
    while len(rows) < N_VEHICLES:
        plate = rand_plate()
        if plate in plates:
            continue
        plates.add(plate)
        make, model, cat = random.choice(VEHICLE_CATALOG)
        rows.append((
            plate,
            make,
            model,
            random.randint(2015, 2024),
            random.choice(COLORS),
            cat,
            random.choices([True, False], weights=[95, 5])[0],
        ))
    result = execute_values(
        cur,
        """INSERT INTO vehicles (plate_number, make, model, year, color, category, is_active)
           VALUES %s RETURNING vehicle_id""",
        rows, fetch=True,
    )
    return [r[0] for r in result]


def insert_vehicle_assignments(cur, vehicle_ids: list[int], driver_ids: list[int]) -> None:
    """
    Each vehicle gets exactly ONE active assignment (unassigned_at IS NULL),
    satisfying the unique partial index. ~25% also get a prior historical record.
    """
    rows = []
    for vid in vehicle_ids:
        current_driver = random.choice(driver_ids)
        active_start   = rand_dt(START_DATE - timedelta(days=180), START_DATE)

        # Optional historical assignment (a different driver, earlier window)
        if random.random() < 0.25:
            past_driver = random.choice(driver_ids)
            past_start  = active_start - timedelta(days=random.randint(90, 400))
            past_end    = active_start - timedelta(days=random.randint(1, 30))
            rows.append((vid, past_driver, past_start, past_end))   # closed

        rows.append((vid, current_driver, active_start, None))      # active

    execute_values(
        cur,
        "INSERT INTO vehicle_assignments (vehicle_id, driver_id, assigned_at, unassigned_at) VALUES %s",
        rows,
    )


def insert_passengers(cur) -> list[int]:
    rows = [
        (
            fake.name(),
            fake.unique.email(),
            fake.unique.numerify("+1-###-###-####"),
            random.choices(PASS_STATUSES, PASS_WEIGHTS)[0],
            rand_dt(START_DATE - timedelta(days=365), START_DATE + timedelta(days=180)),
        )
        for _ in range(N_PASSENGERS)
    ]
    result = execute_values(
        cur,
        "INSERT INTO passengers (name, email, phone_number, status, created_at) VALUES %s RETURNING passenger_id",
        rows, fetch=True,
    )
    return [r[0] for r in result]


# ── trip row builder ──────────────────────────────────────────────────────────

def _build_trip(driver_ids, passenger_ids, vehicle_ids,
                location_ids, pm_ids, promos) -> tuple:
    """Construct one trip tuple respecting all CHECK constraints."""
    requested_at = rand_dt()
    status       = random.choices(TRIP_STATUSES, TRIP_WEIGHTS)[0]
    distance_km  = round(random.uniform(1.0, 95.0), 2)
    base_fare    = round(max(3.00, distance_km * random.uniform(0.8, 1.8)), 2)
    surge        = random.choices(SURGE_VALUES, SURGE_WEIGHTS)[0]

    # Tip: only completed trips
    tip = round(base_fare * random.uniform(0.0, 0.25), 2) if status == "completed" else 0.00

    # Promo code: only ~20% of completed trips
    promo_id = None
    discount  = 0.00
    if status == "completed" and random.random() < 0.20:
        p        = random.choice(promos)
        promo_id = p["id"]
        raw      = (base_fare * p["value"] / 100) if p["type"] == "percent" else p["value"]
        discount = round(min(raw, base_fare), 2)   # satisfies chk_discount_not_exceed_base

    # completed_at: required when status = 'completed' (satisfies chk_completed_at)
    completed_at = None
    if status == "completed":
        duration_min = max(5, int(distance_km * random.uniform(1.5, 4.0)))
        completed_at = requested_at + timedelta(minutes=duration_min)

    # Dual ratings: only on ~85% of completed trips
    driver_rating    = None
    passenger_rating = None
    if status == "completed" and random.random() < 0.85:
        driver_rating    = random.choices(DR_RATING_VALS, DR_RATING_WTS)[0]
        passenger_rating = random.choices(PR_RATING_VALS, PR_RATING_WTS)[0]

    # Payment: not assigned on no_show trips
    payment_id = random.choice(pm_ids) if status != "no_show" else None

    # Pickup ≠ dropoff
    pickup  = random.choice(location_ids)
    dropoff = random.choice([loc for loc in location_ids if loc != pickup])

    return (
        random.choice(driver_ids),
        random.choice(passenger_ids),
        random.choice(vehicle_ids),
        pickup,
        dropoff,
        payment_id,
        promo_id,
        base_fare,
        tip,
        discount,
        surge,
        distance_km,
        status,
        requested_at,
        completed_at,
        driver_rating,
        passenger_rating,
    )


def insert_trips(cur, driver_ids, passenger_ids, vehicle_ids,
                 location_ids, pm_ids, promos) -> list[tuple]:
    """
    Batch-insert all trips in pages of 1 000.
    Returns list of (trip_id, status, requested_at) for the cancellations step.
    """
    print(f"       Building {N_TRIPS:,} rows …", end=" ", flush=True)
    rows = [
        _build_trip(driver_ids, passenger_ids, vehicle_ids, location_ids, pm_ids, promos)
        for _ in range(N_TRIPS)
    ]
    print("done  |  Inserting …", end=" ", flush=True)

    sql = """
        INSERT INTO trips (
            driver_id, passenger_id, vehicle_id,
            pickup_location_id, dropoff_location_id,
            payment_method_id, promo_code_id,
            base_fare, tip_amount, discount_amount, surge_multiplier,
            distance_km, status,
            requested_at, completed_at,
            driver_rating, passenger_rating
        ) VALUES %s
        RETURNING trip_id, status, requested_at
    """
    result = execute_values(cur, sql, rows, page_size=1000, fetch=True)
    print("done.")
    return result   # [(trip_id, status, requested_at), ...]


def insert_trip_cancellations(cur, trip_meta: list[tuple]) -> int:
    """Insert one cancellation record per cancelled trip."""
    cancelled = [(tid, req_at) for tid, status, req_at in trip_meta if status == "cancelled"]

    rows = [
        (
            tid,
            req_at + timedelta(minutes=random.randint(1, 15)),  # cancelled within 15 min
            random.choices(CANCEL_BY, CANCEL_BY_WTS)[0],
            random.choice(CANCEL_REASONS),
        )
        for tid, req_at in cancelled
    ]
    execute_values(
        cur,
        """INSERT INTO trip_cancellations (trip_id, cancelled_at, cancelled_by, cancellation_reason)
           VALUES %s""",
        rows, page_size=500,
    )
    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Connecting to the database …\n")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # ── insert in FK-dependency order ────────────────────────────────────

        print("[1/10]  Locations …")
        location_ids = insert_locations(cur)
        print(f"        ✓ {len(location_ids)} rows\n")

        print("[2/10]  Payment methods …")
        pm_ids = insert_payment_methods(cur)
        print(f"        ✓ {len(pm_ids)} rows\n")

        print("[3/10]  Promo codes …")
        promos = insert_promo_codes(cur)
        print(f"        ✓ {len(promos)} rows\n")

        print("[4/10]  Drivers …")
        driver_ids = insert_drivers(cur)
        print(f"        ✓ {len(driver_ids)} rows\n")

        print("[5/10]  Driver licenses …")
        insert_driver_licenses(cur, driver_ids)
        print(f"        ✓ {len(driver_ids)} rows (1 per driver)\n")

        print("[6/10]  Vehicles …")
        vehicle_ids = insert_vehicles(cur)
        print(f"        ✓ {len(vehicle_ids)} rows\n")

        print("[7/10]  Vehicle assignments …")
        insert_vehicle_assignments(cur, vehicle_ids, driver_ids)
        print("        ✓ done\n")

        print("[8/10]  Passengers …")
        passenger_ids = insert_passengers(cur)
        print(f"        ✓ {len(passenger_ids)} rows\n")

        print("[9/10]  Trips …")
        trip_meta = insert_trips(
            cur, driver_ids, passenger_ids, vehicle_ids,
            location_ids, pm_ids, promos,
        )
        print(f"        ✓ {len(trip_meta):,} rows\n")

        print("[10/10] Trip cancellations …")
        n_cancel = insert_trip_cancellations(cur, trip_meta)
        print(f"        ✓ {n_cancel:,} rows\n")

        conn.commit()
        print("✅  All data committed successfully.\n")

        # ── row-count summary ─────────────────────────────────────────────────
        tables = [
            "locations", "drivers", "driver_licenses",
            "passengers", "vehicles", "vehicle_assignments",
            "payment_methods", "promo_codes", "trips", "trip_cancellations",
        ]
        print("─── Final row counts ─────────────────────────")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"    {table:<25}  {count:>7,}")
        print("──────────────────────────────────────────────")

    except Exception as exc:
        conn.rollback()
        print(f"\n❌  Error — transaction rolled back.\n{exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
