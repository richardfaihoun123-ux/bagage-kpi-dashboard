-- Schéma en étoile : centre de tri bagages (données synthétiques, inspiré d'Orly)
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_daily_kpi;
DROP VIEW  IF EXISTS v_hourly_conveyor_kpi;
DROP TABLE IF EXISTS fact_incident;
DROP TABLE IF EXISTS fact_baggage;
DROP TABLE IF EXISTS dim_flight;
DROP TABLE IF EXISTS dim_conveyor;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_date (
    date_key          INTEGER PRIMARY KEY,      -- AAAAMMJJ
    full_date         TEXT NOT NULL,
    year              INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    day_of_week       INTEGER NOT NULL,         -- 0 = lundi
    is_weekend        INTEGER NOT NULL,
    is_school_holiday INTEGER NOT NULL,
    season            TEXT NOT NULL
);

CREATE TABLE dim_conveyor (
    conveyor_id TEXT PRIMARY KEY,
    terminal    TEXT NOT NULL,
    length_m    INTEGER NOT NULL
);

CREATE TABLE dim_flight (
    flight_id       INTEGER PRIMARY KEY,
    flight_number   TEXT NOT NULL,
    airline         TEXT NOT NULL,
    destination     TEXT NOT NULL,
    terminal        TEXT NOT NULL,
    scheduled_dep   TEXT NOT NULL,
    date_key        INTEGER NOT NULL REFERENCES dim_date(date_key),
    conveyor_id     TEXT NOT NULL REFERENCES dim_conveyor(conveyor_id)
);

CREATE TABLE fact_baggage (
    bag_id         INTEGER PRIMARY KEY,
    flight_id      INTEGER NOT NULL REFERENCES dim_flight(flight_id),
    conveyor_id    TEXT    NOT NULL REFERENCES dim_conveyor(conveyor_id),
    date_key       INTEGER NOT NULL REFERENCES dim_date(date_key),
    checkin_ts     TEXT    NOT NULL,
    loaded_ts      TEXT    NOT NULL,
    processing_min REAL    NOT NULL,
    status         TEXT    NOT NULL CHECK (status IN ('on_time','late','mishandled'))
);

CREATE TABLE fact_incident (
    incident_id  INTEGER PRIMARY KEY,
    conveyor_id  TEXT NOT NULL REFERENCES dim_conveyor(conveyor_id),
    start_ts     TEXT NOT NULL,
    duration_min INTEGER NOT NULL
);

CREATE INDEX ix_bag_date     ON fact_baggage(date_key);
CREATE INDEX ix_bag_conv     ON fact_baggage(conveyor_id);
CREATE INDEX ix_bag_flight   ON fact_baggage(flight_id);
CREATE INDEX ix_bag_checkin  ON fact_baggage(checkin_ts);

-- KPI journaliers (utile pour valider les mesures DAX)
CREATE VIEW v_daily_kpi AS
SELECT d.full_date,
       COUNT(*)                                                        AS bags,
       ROUND(100.0 * SUM(b.status = 'on_time') / COUNT(*), 2)          AS on_time_pct,
       ROUND(1000.0 * SUM(b.status = 'mishandled') / COUNT(*), 2)      AS mishandled_per_1000,
       ROUND(AVG(b.processing_min), 2)                                 AS avg_processing_min
FROM fact_baggage b
JOIN dim_date d USING (date_key)
GROUP BY d.full_date;

-- KPI par convoyeur et par heure (vue « temps réel » / goulots)
CREATE VIEW v_hourly_conveyor_kpi AS
SELECT b.conveyor_id,
       substr(b.checkin_ts, 1, 13) || ':00'                            AS hour_slot,
       COUNT(*)                                                        AS bags,
       ROUND(AVG(b.processing_min), 2)                                 AS avg_processing_min,
       ROUND(100.0 * SUM(b.status <> 'on_time') / COUNT(*), 2)         AS issue_pct
FROM fact_baggage b
GROUP BY b.conveyor_id, substr(b.checkin_ts, 1, 13);
