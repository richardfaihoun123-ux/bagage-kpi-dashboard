-- Valeurs de référence pour contrôler les cartes Power BI (sans aucun filtre)
SELECT COUNT(*)                                                    AS bags,
       ROUND(100.0 * SUM(status = 'on_time')    / COUNT(*), 2)     AS on_time_pct,
       ROUND(100.0 * SUM(status = 'late')       / COUNT(*), 2)     AS late_pct,
       ROUND(1000.0 * SUM(status = 'mishandled') / COUNT(*), 2)    AS mishandled_per_1000,
       ROUND(AVG(processing_min), 2)                               AS avg_processing_min
FROM fact_baggage;

-- Pic horaire (équivalent de [Peak Hour Bags])
SELECT MAX(n) AS peak_hour_bags
FROM (SELECT COUNT(*) AS n FROM fact_baggage GROUP BY substr(checkin_ts, 1, 13));

-- Incidents (équivalent de [Incidents] et [Downtime Min])
SELECT COUNT(*) AS incidents, SUM(duration_min) AS downtime_min FROM fact_incident;

-- Jours en alerte (taux à l'heure < 97 %)
SELECT full_date, bags, on_time_pct, mishandled_per_1000
FROM v_daily_kpi WHERE on_time_pct < 97 ORDER BY on_time_pct;
