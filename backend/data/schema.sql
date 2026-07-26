-- KSP Crime AI — Minimum Viable Schema (Phase 0)
-- Auto-loaded into Postgres on first container start via docker-entrypoint-initdb.d

CREATE TABLE accused (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    address TEXT,
    gang_id INT,
    is_repeat_offender BOOLEAN DEFAULT FALSE
);

CREATE TABLE victim (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    gender VARCHAR(10),
    occupation VARCHAR(100),
    address TEXT
);

CREATE TABLE crime (
    id SERIAL PRIMARY KEY,
    fir_no VARCHAR(30) UNIQUE,
    crime_type VARCHAR(50),
    ipc_sections VARCHAR(100),
    crime_date DATE,
    crime_time TIME,
    description TEXT,
    investigation_status VARCHAR(30), -- e.g. 'Open', 'Solved', 'Under Investigation'
    district VARCHAR(50),
    police_station VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT
);

CREATE TABLE crime_accused (
    crime_id INT REFERENCES crime(id),
    accused_id INT REFERENCES accused(id)
);

CREATE TABLE crime_victim (
    crime_id INT REFERENCES crime(id),
    victim_id INT REFERENCES victim(id)
);

CREATE TABLE vehicle (
    id SERIAL PRIMARY KEY,
    plate_no VARCHAR(20),
    vehicle_type VARCHAR(30),
    owner_accused_id INT REFERENCES accused(id)
);

CREATE TABLE crime_vehicle (
    crime_id INT REFERENCES crime(id),
    vehicle_id INT REFERENCES vehicle(id)
);

-- Helpful indexes for the query patterns Module 1 will generate
CREATE INDEX idx_crime_type ON crime(crime_type);
CREATE INDEX idx_crime_district ON crime(district);
CREATE INDEX idx_crime_status ON crime(investigation_status);
CREATE INDEX idx_crime_date ON crime(crime_date);
