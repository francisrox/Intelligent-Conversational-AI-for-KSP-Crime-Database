-- Module 6 + Module 10 — additive migration, does NOT touch existing tables/data.
-- Apply manually (not auto-loaded like schema.sql, since the Postgres volume
-- already exists from Phase 0):
--
--   Get-Content backend\data\schema_module6_10.sql | docker exec -i ksp_postgres psql -U ksp_user -d ksp_crime

-- ---- Module 10: Role-Based Access & Security ----

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL,  -- Admin, Supervisor, Investigator, Analyst, Viewer
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    action VARCHAR(100),
    endpoint VARCHAR(200),
    detail TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ---- Module 6: Investigator Decision Support (similar-case search) ----

CREATE TABLE IF NOT EXISTS crime_embedding (
    crime_id INT PRIMARY KEY REFERENCES crime(id),
    embedding REAL[]
);
