"""
Step 3 of 6 -- reduce the GTFS feed to something small enough to reason about.

Input : data/raw/gtfs/*.txt        (BMTC feed, 1.5 million stop_times rows)
Output: data/processed/stops.csv
        data/processed/patterns.npz      (stop order + timings per pattern)
        data/processed/patterns_summary.csv

Why patterns instead of trips
    56,856 trips run over only a few thousand distinct stop sequences. A route
    that runs 60 times a day contributes 60 nearly identical rows. Collapsing
    trips into patterns -- one row per (route, direction, stop sequence) --
    cuts the work by about twenty times and changes nothing about which places
    connect to which. Frequency is not thrown away: it comes back as headway.

Timings kept per pattern are the median across that pattern's trips, measured
from the departure at the first stop. Median rather than mean because a
handful of trips in the feed carry obviously broken times.
"""

import numpy as np
import pandas as pd

from settings import (
    CRS_LATLON,
    CRS_METRIC,
    PROCESSED,
    RAW,
    SERVICE_WINDOW_HOURS,
)

GTFS = RAW / "gtfs"


def to_seconds(series):
    """GTFS times can read 25:10:00 for a trip that crosses midnight."""
    parts = series.str.split(":", expand=True).astype("int32")
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def main():
    import geopandas as gpd
    from shapely.geometry import Point

    # ---------------------------------------------------------------- stops --
    # Both trip_id and stop_id look numeric and are not. Bus stations are
    # split into platforms with ids like "20623_PF1", which is why.
    stops = pd.read_csv(GTFS / "stops.txt", dtype={"stop_id": "string"})
    stops = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].dropna()
    stops = stops.drop_duplicates("stop_id")

    pts = gpd.GeoSeries(
        [Point(x, y) for x, y in zip(stops.stop_lon, stops.stop_lat)], crs=CRS_LATLON
    ).to_crs(CRS_METRIC)
    stops["easting"] = pts.x.to_numpy()
    stops["northing"] = pts.y.to_numpy()

    # A few stops in the feed sit far outside the city, usually a typo in the
    # source. Drop anything more than 60 km from the middle of Bengaluru.
    centre_e, centre_n = 781_000, 1_437_000
    away = np.hypot(stops.easting - centre_e, stops.northing - centre_n)
    strays = int((away > 60_000).sum())
    if strays:
        print(f"  dropping {strays} stops more than 60 km from the city centre")
    stops = stops[away <= 60_000].reset_index(drop=True)

    stops = stops.reset_index(drop=True)
    stops["stop_idx"] = np.arange(len(stops))
    stop_pos = dict(zip(stops.stop_id, stops.stop_idx))

    # ------------------------------------------------------------- stop_times --
    print("reading stop_times ...")
    times = pd.read_csv(
        GTFS / "stop_times.txt",
        usecols=["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        # trip_id is NOT numeric in this feed. Most look like "1042", but a
        # few thousand read "21172_PF9". Reading them as int64 blows up on
        # row ~900,000, which cost me an evening.
        dtype={"trip_id": "string", "stop_id": "string", "stop_sequence": "int32"},
    )
    times["arr_s"] = to_seconds(times["arrival_time"])
    times["dep_s"] = to_seconds(times["departure_time"])
    times = times.drop(columns=["arrival_time", "departure_time"])

    times["stop_idx"] = times["stop_id"].map(stop_pos)
    before = len(times)
    times = times.dropna(subset=["stop_idx"])
    times["stop_idx"] = times["stop_idx"].astype("int32")
    if before != len(times):
        print(f"  dropped {before - len(times):,} stop_times rows on removed stops")

    times = times.sort_values(["trip_id", "stop_sequence"], kind="stable")

    trips = pd.read_csv(
        GTFS / "trips.txt",
        usecols=["trip_id", "route_id", "direction_id"],
        dtype={"trip_id": "string"},
    )
    times = times.merge(trips, on="trip_id", how="left")

    # ------------------------------------------------------------- patterns --
    # A pattern is a route plus a direction plus the exact list of stops.
    print("collapsing trips into patterns ...")
    grouped = times.groupby("trip_id", sort=False)
    trip_stops = grouped["stop_idx"].apply(tuple)
    trip_start = grouped["dep_s"].first()
    trip_elapsed = grouped["arr_s"].apply(lambda s: tuple(s.to_numpy() - s.to_numpy()[0]))
    trip_meta = trips.set_index("trip_id").loc[trip_stops.index]

    frame = pd.DataFrame(
        {
            "route_id": trip_meta["route_id"].to_numpy(),
            "direction_id": trip_meta["direction_id"].fillna(0).astype(int).to_numpy(),
            "stops": trip_stops.to_numpy(),
            "elapsed": trip_elapsed.to_numpy(),
            "start_s": trip_start.to_numpy(),
        },
        index=trip_stops.index,
    )
    frame["key"] = list(zip(frame.route_id, frame.direction_id, frame.stops))

    # --------------------------------------------------- throw out bad trips --
    # Some trips in the feed have times that go backwards, or claim an eleven
    # hour run across the city. Those are scraping artefacts, not services.
    # Three tests, all of them things a real bus cannot do:
    #   - the whole trip takes more than five hours
    #   - one hop between adjacent stops takes more than an hour
    #   - a trip with two or more stops takes no time at all
    def trip_is_sane(elapsed):
        arr = np.asarray(elapsed, dtype=float)
        if len(arr) < 2:
            return False
        gaps = np.diff(arr)
        if arr[-1] > 300 * 60 or arr[-1] <= 0:
            return False
        if gaps.max() > 60 * 60 or gaps.min() < -60:
            return False
        return True

    sane = frame["elapsed"].map(trip_is_sane)
    print(f"  discarding {int((~sane).sum()):,} trips with impossible timings "
          f"({(~sane).mean():.1%} of the feed)")
    frame = frame[sane]

    pattern_stops = []
    pattern_times = []
    rows = []
    for (route_id, direction_id, seq), block in frame.groupby("key", sort=False):
        n_trips = len(block)
        elapsed = np.median(np.vstack(block["elapsed"].to_numpy()), axis=0)

        # Times must not go backwards along a pattern.
        elapsed = np.maximum.accumulate(elapsed)

        # Headway: how long between one bus and the next on this pattern.
        # Most BMTC routes in this feed run a handful of times a day, so this
        # number is often measured in hours rather than minutes. That is a
        # real feature of the network, not a bug in the parsing.
        headway_min = SERVICE_WINDOW_HOURS * 60 / n_trips

        pattern_stops.append(np.asarray(seq, dtype=np.int32))
        pattern_times.append((elapsed / 60.0).astype(np.float32))
        rows.append(
            {
                "route_id": route_id,
                "direction_id": direction_id,
                "n_stops": len(seq),
                "n_trips": n_trips,
                "headway_min": headway_min,
                "run_time_min": elapsed[-1] / 60.0,
                "first_dep_s": int(block["start_s"].min()),
                "last_dep_s": int(block["start_s"].max()),
            }
        )

    summary = pd.DataFrame(rows)
    summary.insert(0, "pattern_id", np.arange(len(summary)))

    routes = pd.read_csv(GTFS / "routes.txt", usecols=["route_id", "route_short_name"])
    summary = summary.merge(routes, on="route_id", how="left")

    # Flatten the ragged pattern arrays so they survive a save/load round trip.
    lengths = np.array([len(p) for p in pattern_stops], dtype=np.int32)
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    flat_stops = np.concatenate(pattern_stops).astype(np.int32)
    flat_times = np.concatenate(pattern_times).astype(np.float32)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        PROCESSED / "patterns.npz",
        offsets=offsets,
        stops=flat_stops,
        elapsed_min=flat_times,
        headway_min=summary["headway_min"].to_numpy(np.float32),
    )
    stops.to_csv(PROCESSED / "stops.csv", index=False)
    summary.to_csv(PROCESSED / "patterns_summary.csv", index=False)

    print()
    print(f"stops kept          : {len(stops):,}")
    print(f"trips read          : {frame.shape[0]:,}")
    print(f"patterns built      : {len(summary):,}")
    print(f"stop visits stored  : {len(flat_stops):,}")
    print(f"median headway      : {summary.headway_min.median():.0f} min")
    print(f"routes with headway under 15 min: "
          f"{(summary.headway_min < 15).sum():,} patterns")
    print(f"longest run time    : {summary.run_time_min.max():.0f} min")
    frequent = summary[summary.headway_min <= 30]
    print(f"patterns every 30 min or better : {len(frequent):,} "
          f"({len(frequent) / len(summary):.1%})")


if __name__ == "__main__":
    main()
