"""
KSP Crime AI — Postgres -> Neo4j Graph Sync (Module 2)

Postgres remains the source of truth for records (Module 1 queries it directly).
This script mirrors that same data into Neo4j as a graph, because "find hidden
connections between people/vehicles across cases" is a graph problem — doing it
with SQL joins gets messy fast, this makes it a straightforward Cypher traversal.

Graph model:
  (:Accused {id, name, age, gender, is_repeat_offender, gang_id})
  (:Crime {id, fir_no, crime_type, crime_date, district, police_station, investigation_status})
  (:Vehicle {id, plate_no, vehicle_type})
  (:Victim {id, name})

  (:Accused)-[:ACCUSED_IN]->(:Crime)
  (:Crime)-[:INVOLVES_VEHICLE]->(:Vehicle)
  (:Vehicle)-[:OWNED_BY]->(:Accused)
  (:Crime)-[:HAS_VICTIM]->(:Victim)

Run with:
  docker exec -it ksp_backend python data/sync_to_neo4j.py

Safe to re-run — clears the graph first, then rebuilds it from current Postgres data.
Re-run this any time you regenerate the Postgres dataset.
"""

import os
import psycopg2
from neo4j import GraphDatabase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ksp_user:ksp_pass@localhost:5432/ksp_crime")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "ksp_graph_pass")

BATCH_SIZE = 500


def fetch_all(pg_cur, query):
    pg_cur.execute(query)
    columns = [desc[0] for desc in pg_cur.description]
    return [dict(zip(columns, row)) for row in pg_cur.fetchall()]


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def main():
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cur = pg_conn.cursor()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("Clearing existing graph...")
        session.run("MATCH (n) DETACH DELETE n")

        print("Creating constraints (for fast MERGE lookups)...")
        session.run("CREATE CONSTRAINT accused_id IF NOT EXISTS FOR (a:Accused) REQUIRE a.id IS UNIQUE")
        session.run("CREATE CONSTRAINT crime_id IF NOT EXISTS FOR (c:Crime) REQUIRE c.id IS UNIQUE")
        session.run("CREATE CONSTRAINT vehicle_id IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE")
        session.run("CREATE CONSTRAINT victim_id IF NOT EXISTS FOR (vi:Victim) REQUIRE vi.id IS UNIQUE")

        # ---- Nodes ----

        print("Loading Accused nodes...")
        accused = fetch_all(pg_cur, "SELECT id, name, age, gender, is_repeat_offender, gang_id FROM accused")
        for batch in chunks(accused, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MERGE (a:Accused {id: row.id})
                   SET a.name = row.name, a.age = row.age, a.gender = row.gender,
                       a.is_repeat_offender = row.is_repeat_offender, a.gang_id = row.gang_id""",
                rows=batch,
            )

        print("Loading Crime nodes...")
        crimes = fetch_all(
            pg_cur,
            """SELECT id, fir_no, crime_type, crime_date::text AS crime_date,
                      district, police_station, investigation_status
               FROM crime""",
        )
        for batch in chunks(crimes, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MERGE (c:Crime {id: row.id})
                   SET c.fir_no = row.fir_no, c.crime_type = row.crime_type,
                       c.crime_date = row.crime_date, c.district = row.district,
                       c.police_station = row.police_station,
                       c.investigation_status = row.investigation_status""",
                rows=batch,
            )

        print("Loading Vehicle nodes...")
        vehicles = fetch_all(pg_cur, "SELECT id, plate_no, vehicle_type, owner_accused_id FROM vehicle")
        for batch in chunks(vehicles, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MERGE (v:Vehicle {id: row.id})
                   SET v.plate_no = row.plate_no, v.vehicle_type = row.vehicle_type""",
                rows=batch,
            )

        print("Loading Victim nodes...")
        victims = fetch_all(pg_cur, "SELECT id, name FROM victim")
        for batch in chunks(victims, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MERGE (vi:Victim {id: row.id})
                   SET vi.name = row.name""",
                rows=batch,
            )

        # ---- Relationships ----

        print("Creating ACCUSED_IN relationships (Accused -> Crime)...")
        crime_accused = fetch_all(pg_cur, "SELECT crime_id, accused_id FROM crime_accused")
        for batch in chunks(crime_accused, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MATCH (a:Accused {id: row.accused_id}), (c:Crime {id: row.crime_id})
                   MERGE (a)-[:ACCUSED_IN]->(c)""",
                rows=batch,
            )

        print("Creating INVOLVES_VEHICLE relationships (Crime -> Vehicle)...")
        crime_vehicle = fetch_all(pg_cur, "SELECT crime_id, vehicle_id FROM crime_vehicle")
        for batch in chunks(crime_vehicle, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MATCH (c:Crime {id: row.crime_id}), (v:Vehicle {id: row.vehicle_id})
                   MERGE (c)-[:INVOLVES_VEHICLE]->(v)""",
                rows=batch,
            )

        print("Creating OWNED_BY relationships (Vehicle -> Accused)...")
        for batch in chunks(vehicles, BATCH_SIZE):
            owned = [v for v in batch if v["owner_accused_id"] is not None]
            if owned:
                session.run(
                    """UNWIND $rows AS row
                       MATCH (v:Vehicle {id: row.id}), (a:Accused {id: row.owner_accused_id})
                       MERGE (v)-[:OWNED_BY]->(a)""",
                    rows=owned,
                )

        print("Creating HAS_VICTIM relationships (Crime -> Victim)...")
        crime_victim = fetch_all(pg_cur, "SELECT crime_id, victim_id FROM crime_victim")
        for batch in chunks(crime_victim, BATCH_SIZE):
            session.run(
                """UNWIND $rows AS row
                   MATCH (c:Crime {id: row.crime_id}), (vi:Victim {id: row.victim_id})
                   MERGE (c)-[:HAS_VICTIM]->(vi)""",
                rows=batch,
            )

        # Sanity counts
        counts = session.run(
            """MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY label"""
        ).data()
        print("Node counts by label:", counts)

        rel_counts = session.run(
            """MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS count ORDER BY rel_type"""
        ).data()
        print("Relationship counts by type:", rel_counts)

    driver.close()
    pg_cur.close()
    pg_conn.close()
    print("Done. Graph sync complete.")


if __name__ == "__main__":
    main()
