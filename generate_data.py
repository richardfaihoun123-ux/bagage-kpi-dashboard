#!/usr/bin/env python3
"""
Générateur de données synthétiques : centre de tri bagages (inspiré de Paris-Orly).

Produit :
  - data/bagage_kpi.db          base SQLite (schéma en étoile, cf. sql/schema.sql)
  - data/csv/*.csv              mêmes tables en CSV (import direct dans Power BI)

Toutes les données sont FICTIVES. Les ordres de grandeur viennent de l'offre de stage :
15 km de convoyeurs, ~20 M de bagages/an, pics à ~90 000 bagages/jour
(soit un rapport pic / moyenne journalière d'environ 1,6).

Par défaut, l'échantillon est à l'échelle 500 000 bagages (≈ 1/40e du trafic réel) ;
le rapport pic/moyenne et les taux de service sont conservés.

Usage :
    python generate_data.py --bags 500000 --start 2025-10-01 --seed 42
"""
import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent

# --- Paramètres du système (fictifs) ----------------------------------------
# 12 convoyeurs, 15 000 m au total
CONVEYORS = [
    ("C01", "Orly 1-2", 1600), ("C02", "Orly 1-2", 1500), ("C03", "Orly 1-2", 1400),
    ("C04", "Orly 1-2", 1300), ("C05", "Orly 1-2", 1300), ("C06", "Orly 1-2", 1250),
    ("C07", "Orly 3-4", 1200), ("C08", "Orly 3-4", 1150), ("C09", "Orly 3-4", 1100),
    ("C10", "Orly 3-4", 1000), ("C11", "Orly 3-4", 1000), ("C12", "Orly 3-4", 1200),
]
AIRLINES = [("AF", 0.30), ("TO", 0.14), ("VY", 0.08), ("AH", 0.07), ("TU", 0.06),
            ("AT", 0.06), ("IB", 0.05), ("TP", 0.05), ("EK", 0.04), ("DT", 0.04),
            ("SS", 0.04), ("KL", 0.03), ("LH", 0.04)]
DESTINATIONS = ["ALG", "CMN", "RAK", "LIS", "OPO", "MAD", "BCN", "FCO", "ATH", "TUN",
                "DXB", "FDF", "PTP", "RUN", "BKO", "DKR", "IST", "ORN", "AJA", "NCE"]

# Profil horaire des départs (heures 5 -> 23), part relative
HOUR_PROFILE = {5: 3, 6: 8, 7: 9, 8: 8, 9: 6, 10: 5, 11: 5, 12: 5, 13: 5, 14: 5,
                15: 6, 16: 8, 17: 9, 18: 9, 19: 7, 20: 5, 21: 3, 22: 2, 23: 1}

# Vacances scolaires approximatives (fictives, juste pour structurer la saisonnalité)
HOLIDAYS = [("2025-10-18", "2025-11-03"), ("2025-12-20", "2026-01-05"),
            ("2026-02-14", "2026-03-02"), ("2026-04-11", "2026-04-27"),
            ("2026-07-04", "2026-08-31")]
SUMMER = ("2026-07-04", "2026-08-31")

BAGS_PER_FLIGHT = 70
CUTOFF_MIN = 20          # un bagage doit être chargé 20 min avant le départ
N_INCIDENTS = 45


def build_calendar(start: str, days: int, rng) -> pd.DataFrame:
    dates = pd.date_range(start, periods=days, freq="D")
    cal = pd.DataFrame({"full_date": dates})
    cal["date_key"] = cal.full_date.dt.strftime("%Y%m%d").astype(int)
    cal["year"] = cal.full_date.dt.year
    cal["month"] = cal.full_date.dt.month
    cal["day_of_week"] = cal.full_date.dt.dayofweek
    cal["is_weekend"] = (cal.day_of_week >= 5).astype(int)

    cal["is_school_holiday"] = 0
    for a, b in HOLIDAYS:
        cal.loc[cal.full_date.between(a, b), "is_school_holiday"] = 1
    is_summer = cal.full_date.between(*SUMMER)
    cal["season"] = np.select(
        [is_summer, cal.month.isin([12, 1, 2]), cal.month.isin([3, 4, 5])],
        ["ete", "hiver", "printemps"], default="automne")

    # Poids de trafic journalier : saison x jour de semaine x bruit
    dow = cal.day_of_week.map({0: .92, 1: .86, 2: .88, 3: .98, 4: 1.12, 5: 1.05, 6: 1.15})
    w = (1 + 0.32 * is_summer + 0.14 * (cal.is_school_holiday & ~is_summer)) * dow
    # « grands départs » : samedis de début juillet / août
    big = cal.full_date.isin(pd.to_datetime(["2026-07-04", "2026-07-11", "2026-07-25", "2026-08-01"]))
    w = w * (1 + 0.20 * big) * rng.lognormal(0, 0.04, len(cal))
    cal["traffic_weight"] = w / w.mean()
    return cal


def build_flights(cal: pd.DataFrame, total_bags: int, rng) -> pd.DataFrame:
    n_per_day = np.maximum(1, np.round(cal.traffic_weight * total_bags / len(cal) / BAGS_PER_FLIGHT)).astype(int)
    day_idx = np.repeat(np.arange(len(cal)), n_per_day)
    n = len(day_idx)

    hours = np.array(list(HOUR_PROFILE))
    p = np.array(list(HOUR_PROFILE.values()), dtype=float)
    hour = rng.choice(hours, size=n, p=p / p.sum())
    minute = rng.choice(np.arange(0, 60, 5), size=n)
    sched = (cal.full_date.values[day_idx]
             + hour.astype("timedelta64[h]") + minute.astype("timedelta64[m]"))

    airline = rng.choice([a for a, _ in AIRLINES], size=n, p=[w for _, w in AIRLINES])
    terminal = rng.choice(["Orly 1-2", "Orly 3-4"], size=n, p=[0.45, 0.55])

    conv = pd.DataFrame(CONVEYORS, columns=["conveyor_id", "terminal", "length_m"])
    conveyor = np.empty(n, dtype=object)
    for term, grp in conv.groupby("terminal"):
        mask = terminal == term
        conveyor[mask] = rng.choice(grp.conveyor_id, size=mask.sum(), p=grp.length_m / grp.length_m.sum())

    flights = pd.DataFrame({
        "flight_id": np.arange(1, n + 1),
        "flight_number": [f"{a}{x}" for a, x in zip(airline, rng.integers(100, 9999, n))],
        "airline": airline,
        "destination": rng.choice(DESTINATIONS, size=n),
        "terminal": terminal,
        "scheduled_dep": pd.to_datetime(sched),
        "date_key": cal.date_key.values[day_idx],
        "conveyor_id": conveyor,
        "day_weight": cal.traffic_weight.values[day_idx],
        "n_bags": np.maximum(10, rng.poisson(BAGS_PER_FLIGHT, n)),
    })
    return flights


def build_bags(flights: pd.DataFrame, rng) -> pd.DataFrame:
    conv = pd.DataFrame(CONVEYORS, columns=["conveyor_id", "terminal", "length_m"])
    rep = np.repeat(np.arange(len(flights)), flights.n_bags.values)
    bags = pd.DataFrame({
        "flight_id": flights.flight_id.values[rep],
        "conveyor_id": flights.conveyor_id.values[rep],
        "terminal": flights.terminal.values[rep],
        "date_key": flights.date_key.values[rep],
        "sched_dep": flights.scheduled_dep.values[rep],
        "day_weight": flights.day_weight.values[rep],
    })
    n = len(bags)

    # 10 % de débordement vers un autre convoyeur du même terminal
    over = rng.random(n) < 0.10
    for term, grp in conv.groupby("terminal"):
        m = over & (bags.terminal.values == term)
        bags.loc[m, "conveyor_id"] = rng.choice(grp.conveyor_id, size=m.sum())

    # Dépôt : au moins 30 min avant le départ, en moyenne ~1 h 40 avant
    offset_min = 30 + rng.gamma(2.5, 28.0, n)
    bags["checkin_ts"] = bags.sched_dep - pd.to_timedelta(offset_min, unit="m")

    # Durée de traitement : lognormale, plus longue sur les convoyeurs longs
    length = bags.conveyor_id.map(conv.set_index("conveyor_id").length_m).values
    median = 6 + length / 150
    # Congestion = intensité du jour x intensité de l'heure de dépôt
    h = bags.checkin_ts.dt.hour.values
    prof = pd.Series(HOUR_PROFILE).reindex(range(24), fill_value=1).values
    hour_load = prof[h] / np.average(prof, weights=prof)
    congestion = bags.day_weight.values * hour_load
    slowdown = 1 + 0.55 * np.clip(congestion - 1.25, 0, None)
    proc = rng.lognormal(np.log(median), 0.38, n) * slowdown

    # Incidents (pannes) : surcroît de délai et de risque sur le convoyeur touché
    cal_start, cal_end = bags.checkin_ts.min(), bags.checkin_ts.max()
    span_min = int((cal_end - cal_start).total_seconds() // 60)
    incidents = pd.DataFrame({
        "incident_id": np.arange(1, N_INCIDENTS + 1),
        "conveyor_id": rng.choice([c[0] for c in CONVEYORS], N_INCIDENTS),
        "start_ts": cal_start + pd.to_timedelta(rng.integers(0, span_min, N_INCIDENTS), unit="m"),
        "duration_min": rng.integers(15, 150, N_INCIDENTS),
    })
    p_mis = 0.005 + 0.003 * np.clip(congestion - 1.25, 0, None)
    ts, cid = bags.checkin_ts.values, bags.conveyor_id.values
    for r in incidents.itertuples():
        end = r.start_ts + pd.Timedelta(minutes=int(r.duration_min))
        m = (cid == r.conveyor_id) & (ts >= r.start_ts.to_datetime64()) & (ts <= end.to_datetime64())
        proc[m] += rng.uniform(8, r.duration_min * 0.7, m.sum())
        p_mis[m] += 0.03

    bags["processing_min"] = proc.round(2)
    bags["loaded_ts"] = bags.checkin_ts + pd.to_timedelta(proc, unit="m")

    cutoff = bags.sched_dep - pd.Timedelta(minutes=CUTOFF_MIN)
    mishandled = rng.random(n) < p_mis
    bags["status"] = np.select([mishandled, bags.loaded_ts > cutoff], ["mishandled", "late"], default="on_time")
    bags.insert(0, "bag_id", np.arange(1, n + 1))
    return bags[["bag_id", "flight_id", "conveyor_id", "date_key", "checkin_ts",
                 "loaded_ts", "processing_min", "status"]], incidents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bags", type=int, default=500_000, help="nombre approximatif de bagages")
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    cal = build_calendar(args.start, args.days, rng)
    flights = build_flights(cal, args.bags, rng)
    bags, incidents = build_bags(flights, rng)
    conv = pd.DataFrame(CONVEYORS, columns=["conveyor_id", "terminal", "length_m"])

    # --- Mise en forme pour l'export ---
    fmt = "%Y-%m-%d %H:%M:%S"
    dim_date = cal.drop(columns="traffic_weight").assign(full_date=cal.full_date.dt.strftime("%Y-%m-%d"))
    dim_flight = flights.drop(columns=["day_weight", "n_bags"]).assign(
        scheduled_dep=flights.scheduled_dep.dt.strftime(fmt))
    fact = bags.assign(checkin_ts=bags.checkin_ts.dt.strftime(fmt), loaded_ts=bags.loaded_ts.dt.strftime(fmt))
    inc = incidents.assign(start_ts=incidents.start_ts.dt.strftime(fmt))
    tables = {"dim_date": dim_date, "dim_conveyor": conv, "dim_flight": dim_flight,
              "fact_baggage": fact, "fact_incident": inc}

    out = ROOT / "data"
    (out / "csv").mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out / "csv" / f"{name}.csv", index=False)

    db = out / "bagage_kpi.db"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    for name, df in tables.items():
        df.to_sql(name, con, if_exists="append", index=False, chunksize=100_000)
    con.commit()

    # --- Contrôle rapide ---
    daily = bags.groupby("date_key").size()
    print(f"Bagages : {len(bags):,} | vols : {len(flights):,} | jours : {len(cal)}")
    print(f"Moyenne/jour : {daily.mean():,.0f} | pic : {daily.max():,} | rapport pic/moyenne : {daily.max()/daily.mean():.2f}")
    print(bags.status.value_counts(normalize=True).round(4).to_string())
    print(f"Mal acheminés pour 1 000 : {1000 * (bags.status == 'mishandled').mean():.1f}")
    print(f"Traitement : médiane {bags.processing_min.median():.1f} min | P95 {bags.processing_min.quantile(.95):.1f} min")
    con.close()
    print(f"\nBase : {db}\nCSV  : {out / 'csv'}")


if __name__ == "__main__":
    main()
