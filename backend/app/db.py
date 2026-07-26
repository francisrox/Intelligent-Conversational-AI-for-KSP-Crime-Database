import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ksp_user:ksp_pass@localhost:5432/ksp_crime")


def get_connection():
    return psycopg2.connect(DATABASE_URL)
