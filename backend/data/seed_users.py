"""
KSP Crime AI — Seed Demo Users (Module 10)

Run with:
  docker exec -it ksp_backend python data/seed_users.py

Safe to re-run — updates password/role if the username already exists.
"""

import os
import psycopg2
import bcrypt

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ksp_user:ksp_pass@localhost:5432/ksp_crime")

# username, password, role — demo credentials only, not for real deployment
DEMO_USERS = [
    ("admin", "admin_password", "Admin"),
    ("supervisor1", "supervisor1_password", "Supervisor"),
    ("investigator1", "investigator1_password", "Investigator"),
    ("analyst1", "analyst1_password", "Analyst"),
    ("viewer1", "viewer1_password", "Viewer"),
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for username, password, role in DEMO_USERS:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            """INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)
               ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role""",
            (username, pw_hash, role),
        )

    conn.commit()
    cur.close()
    conn.close()

    print("Seeded demo users:")
    for username, password, role in DEMO_USERS:
        print(f"  {username} / {password}   ({role})")


if __name__ == "__main__":
    main()
