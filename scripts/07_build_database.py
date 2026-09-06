"""
Load the finished tables into a small SQLite file so the questions in sql/
can be asked in SQL rather than in pandas.

Output: data/processed/bus_access.db

Tables
    wards        one row per BBMP ward, with its journey time and band
    hospitals    the 51 hospital sites and their type
    stops        every BMTC stop with its journey time to a hospital
    grid_points  the 11,345 sample points behind the ward medians
    patterns     one row per route pattern, with headway
"""

import sqlite3

import pandas as pd

from settings import PROCESSED

DB = PROCESSED / "bus_access.db"

TABLES = {
    "wards": "ward_access.csv",
    "hospitals": "hospitals.csv",
    "stops": "stop_access.csv",
    "grid_points": "grid_points.csv",
    "patterns": "patterns_summary.csv",
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_grid_ward ON grid_points(ward_no)",
    "CREATE INDEX IF NOT EXISTS ix_wards_band ON wards(band)",
    "CREATE INDEX IF NOT EXISTS ix_stops_best ON stops(best_min)",
]


def main():
    if DB.exists():
        DB.unlink()
    connection = sqlite3.connect(DB)
    for table, filename in TABLES.items():
        frame = pd.read_csv(PROCESSED / filename)
        frame.to_sql(table, connection, index=False)
        print(f"{table:12s} {len(frame):>7,} rows")
    for statement in INDEXES:
        connection.execute(statement)
    connection.commit()
    connection.close()
    print(f"\nwrote {DB}")


if __name__ == "__main__":
    main()
