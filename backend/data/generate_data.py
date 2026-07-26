"""
KSP Crime AI — Synthetic Data Generator (Phase 0)

Generates a fake-but-consistent dataset:
  ~300 accused, ~400 victims, ~150 vehicles, ~800 crimes

Deliberately plants:
  - "Repeat offenders": a subset of accused linked to 3-6 crimes each
  - "Shared vehicles across districts": a few vehicles used in crimes in
    *different* districts by *different* accused — this is the hidden-connection
    seed that Module 2 (Network Analysis) will later surface.

Run with:
  docker exec -it ksp_backend python data/generate_data.py
"""

import os
import random
import psycopg2
from faker import Faker

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ksp_user:ksp_pass@localhost:5432/ksp_crime")

# Fixed vocab — NL->SQL depends on these being consistent, exact strings
CRIME_TYPES = ["Burglary", "Robbery", "Theft", "Cybercrime", "Assault"]
STATUSES = ["Open", "Solved", "Under Investigation"]
GENDERS = ["Male", "Female"]
VEHICLE_TYPES = ["Two-Wheeler", "Car", "Auto-Rickshaw", "Van"]

# Karnataka-flavored districts/police stations so demo questions
# ("Whitefield", "Mysuru", "Bengaluru") resolve correctly
DISTRICT_STATIONS = {
    "Bengaluru": ["Whitefield", "Indiranagar", "Koramangala", "Yeshwanthpur", "Jayanagar"],
    "Mysuru": ["Devaraja", "Krishnaraja", "Nazarbad"],
    "Mangaluru": ["Bunder", "Kavoor", "Kadri"],
    "Belagavi": ["Camp", "Shahapur", "Tilakwadi"],
    "Hubballi": ["Gokul Road", "Vidyanagar", "Old Hubli"],
}

N_ACCUSED = 300
N_VICTIMS = 400
N_VEHICLES = 150
N_CRIMES = 800
N_REPEAT_OFFENDERS = 35        # subset of accused tied to multiple crimes
N_PLANTED_SHARED_VEHICLES = 8  # vehicles deliberately reused across districts


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def gen_accused(cur, n):
    ids = []
    for _ in range(n):
        cur.execute(
            """INSERT INTO accused (name, age, gender, address, gang_id, is_repeat_offender)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (
                fake.name(),
                random.randint(18, 55),
                random.choice(GENDERS),
                fake.address().replace("\n", ", "),
                random.choice([None, None, None, random.randint(1, 15)]),  # ~25% gang-linked
                False,  # set True later for planted repeat offenders
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def gen_victims(cur, n):
    ids = []
    for _ in range(n):
        cur.execute(
            """INSERT INTO victim (name, age, gender, occupation, address)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (
                fake.name(),
                random.randint(10, 80),
                random.choice(GENDERS),
                fake.job(),
                fake.address().replace("\n", ", "),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def gen_vehicles(cur, n, accused_ids):
    ids = []
    for _ in range(n):
        cur.execute(
            """INSERT INTO vehicle (plate_no, vehicle_type, owner_accused_id)
               VALUES (%s, %s, %s) RETURNING id""",
            (
                f"KA-{random.randint(1,60):02d}-{fake.random_uppercase_letter()}{fake.random_uppercase_letter()}-{random.randint(1000,9999)}",
                random.choice(VEHICLE_TYPES),
                random.choice(accused_ids),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def gen_crimes(cur, n):
    ids = []
    for _ in range(n):
        district = random.choice(list(DISTRICT_STATIONS.keys()))
        station = random.choice(DISTRICT_STATIONS[district])
        crime_type = random.choice(CRIME_TYPES)
        cur.execute(
            """INSERT INTO crime (fir_no, crime_type, ipc_sections, crime_date, crime_time,
                                   description, investigation_status, district, police_station,
                                   latitude, longitude)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (
                f"FIR-{fake.unique.random_number(digits=6)}",
                crime_type,
                f"IPC {random.randint(299, 511)}",
                fake.date_between(start_date="-18M", end_date="today"),
                fake.time(),
                f"{crime_type} reported in {station}, {district}. {fake.sentence(nb_words=12)}",
                random.choices(STATUSES, weights=[0.4, 0.4, 0.2])[0],
                district,
                station,
                round(random.uniform(12.8, 15.3), 6),   # rough Karnataka lat/lng band
                round(random.uniform(74.5, 78.2), 6),
            ),
        )
        ids.append(cur.fetchone()[0])
    return ids


def link_crimes_to_people_and_vehicles(cur, crime_ids, accused_ids, victim_ids, vehicle_ids):
    for crime_id in crime_ids:
        # 1-2 accused per crime
        for accused_id in random.sample(accused_ids, k=random.choice([1, 1, 2])):
            cur.execute(
                "INSERT INTO crime_accused (crime_id, accused_id) VALUES (%s, %s)",
                (crime_id, accused_id),
            )
        # 1 victim per crime (most crimes have one)
        cur.execute(
            "INSERT INTO crime_victim (crime_id, victim_id) VALUES (%s, %s)",
            (crime_id, random.choice(victim_ids)),
        )
        # ~40% of crimes involve a vehicle
        if random.random() < 0.4:
            cur.execute(
                "INSERT INTO crime_vehicle (crime_id, vehicle_id) VALUES (%s, %s)",
                (crime_id, random.choice(vehicle_ids)),
            )


def plant_repeat_offenders(cur, accused_ids, crime_ids):
    """Pick a subset of accused and tie each to 3-6 crimes across different districts.
    This is what makes Module 5 (Offender Profiling) risk scores meaningful."""
    repeat_ids = random.sample(accused_ids, k=N_REPEAT_OFFENDERS)
    for accused_id in repeat_ids:
        cur.execute("UPDATE accused SET is_repeat_offender = TRUE WHERE id = %s", (accused_id,))
        extra_crimes = random.sample(crime_ids, k=random.randint(3, 6))
        for crime_id in extra_crimes:
            cur.execute(
                "INSERT INTO crime_accused (crime_id, accused_id) VALUES (%s, %s)",
                (crime_id, accused_id),
            )
    return repeat_ids


def plant_shared_vehicles(cur, vehicle_ids, accused_ids, crime_ids):
    """Deliberately reuse a few vehicles across crimes committed by DIFFERENT accused
    in DIFFERENT districts. This is the seeded 'hidden connection' for Module 2 later —
    not used by Module 1, but planting it now means we don't have to regenerate data."""
    shared_vehicles = random.sample(vehicle_ids, k=N_PLANTED_SHARED_VEHICLES)
    for vehicle_id in shared_vehicles:
        involved_crimes = random.sample(crime_ids, k=random.randint(3, 4))
        for crime_id in involved_crimes:
            cur.execute(
                "INSERT INTO crime_vehicle (crime_id, vehicle_id) VALUES (%s, %s)",
                (crime_id, vehicle_id),
            )
            # link a different accused each time to the same crime, using this vehicle
            other_accused = random.choice(accused_ids)
            cur.execute(
                "INSERT INTO crime_accused (crime_id, accused_id) VALUES (%s, %s)",
                (crime_id, other_accused),
            )


def main():
    conn = get_conn()
    cur = conn.cursor()

    print("Clearing existing data (if any)...")
    for table in ["crime_vehicle", "crime_victim", "crime_accused", "vehicle", "crime", "victim", "accused"]:
        cur.execute(f"DELETE FROM {table}")

    print(f"Generating {N_ACCUSED} accused...")
    accused_ids = gen_accused(cur, N_ACCUSED)

    print(f"Generating {N_VICTIMS} victims...")
    victim_ids = gen_victims(cur, N_VICTIMS)

    print(f"Generating {N_VEHICLES} vehicles...")
    vehicle_ids = gen_vehicles(cur, N_VEHICLES, accused_ids)

    print(f"Generating {N_CRIMES} crimes...")
    crime_ids = gen_crimes(cur, N_CRIMES)

    print("Linking crimes to accused/victims/vehicles...")
    link_crimes_to_people_and_vehicles(cur, crime_ids, accused_ids, victim_ids, vehicle_ids)

    print(f"Planting {N_REPEAT_OFFENDERS} repeat offenders...")
    plant_repeat_offenders(cur, accused_ids, crime_ids)

    print(f"Planting {N_PLANTED_SHARED_VEHICLES} cross-district shared vehicles...")
    plant_shared_vehicles(cur, vehicle_ids, accused_ids, crime_ids)

    conn.commit()
    cur.close()
    conn.close()
    print("Done. Data generation complete.")


if __name__ == "__main__":
    main()
