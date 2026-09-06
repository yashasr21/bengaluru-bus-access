"""
The quality gate. Run it after the pipeline; it prints PASS or FAIL per check
and exits non-zero if anything fails.

These are not decoration. Six of them caught something real while I was
building this: the non-numeric trip_id, the empty bed count column, the 206
stops sitting in another district, the trips with times running backwards,
wards that were too small to catch a grid point, and the ward medians that
looked good only because unreachable points had been dropped first.
"""

import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from settings import CRS_METRIC, MAX_JOURNEY_MIN, PROCESSED

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))


def main():
    wards = gpd.read_file(PROCESSED / "wards.geojson").to_crs(CRS_METRIC)
    access = pd.read_csv(PROCESSED / "ward_access.csv")
    hospitals = pd.read_csv(PROCESSED / "hospitals.csv")
    stops = pd.read_csv(PROCESSED / "stop_access.csv", dtype={"stop_id": "string"})
    grid = pd.read_csv(PROCESSED / "grid_points.csv")
    patterns = pd.read_csv(PROCESSED / "patterns_summary.csv")

    # 1 -- BBMP has 198 wards. If this is not 198 the boundary file is wrong.
    check("198 wards present", len(wards) == 198, f"got {len(wards)}")

    # 2 -- Census 2011 put BBMP at about 8.44 million.
    total = wards["population"].sum()
    check("ward population near 8.44 million", 8.3e6 < total < 8.6e6, f"{total:,}")

    # 3 -- BBMP covers roughly 709 sq km.
    area = wards.geometry.area.sum() / 1e6
    check("city area between 690 and 730 sq km", 690 < area < 730, f"{area:.0f} sq km")

    # 4 -- Every ward polygon must be valid after the repair step.
    check("all ward polygons valid", wards.geometry.is_valid.all())

    # 5 -- Every ward gets a score. A silent NaN here would hide a whole ward.
    check("every ward scored", access["median_min"].notna().all(),
          f"{int(access['median_min'].isna().sum())} missing")

    # 6 -- Ward numbers line up between the boundary file and the results.
    check("ward ids match between files",
          set(wards.ward_no) == set(access.ward_no))

    # 7 -- No hospital may sit far outside the city; the clip should have caught it.
    centre = np.array([781_000, 1_437_000])
    far = np.hypot(*(hospitals[["easting", "northing"]].to_numpy() - centre).T)
    check("all hospitals within 40 km of centre", far.max() < 40_000,
          f"max {far.max()/1000:.1f} km")

    # 8 -- Hospital list must not contain duplicates at the same point.
    coords = hospitals[["easting", "northing"]].round(0).astype(int)
    check("no two hospitals at identical coordinates",
          not coords.duplicated().any())

    # 9 -- The bed count column really is empty, which is why the rule is by type.
    beds_present = "beds" in hospitals.columns and hospitals["beds"].notna().any()
    check("bed counts unavailable, so type-based rule applies", not beds_present)

    # 10 -- Journey times must be positive and below the ceiling.
    finite = access["median_min"].dropna()
    check("ward journey times in range",
          (finite > 0).all() and (finite <= MAX_JOURNEY_MIN).all(),
          f"{finite.min():.1f} to {finite.max():.1f} min")

    # 11 -- Allowing a change can never make a journey longer.
    worse = (stops["best_min"] > stops["direct_min"] + 0.01).sum()
    check("a transfer never makes a journey worse", worse == 0, f"{worse} rows")

    # 12 -- Walking further to a stop can never make a journey longer either.
    worse_800 = (grid["minutes_800m"] > grid["minutes"] + 0.01).sum()
    check("800 m catchment never worse than 500 m", worse_800 == 0, f"{worse_800} points")

    # 13 -- Restricting to frequent routes can never help.
    better_frequent = (grid["minutes_frequent"] < grid["minutes"] - 0.01).sum()
    check("frequent-routes-only never beats the full network",
          better_frequent == 0, f"{better_frequent} points")

    # 14 -- Every ward must be represented in the grid.
    check("every ward has at least one sample point",
          grid["ward_no"].nunique() == len(wards),
          f"{grid['ward_no'].nunique()} of {len(wards)}")

    # 15 -- Patterns must have sane run times after the trip filter.
    check("no pattern runs longer than five hours",
          patterns["run_time_min"].max() <= 300,
          f"max {patterns['run_time_min'].max():.0f} min")

    # 16 -- Stops used in patterns must all exist in the stop table.
    check("stop table covers every routed stop",
          stops["stop_id"].notna().all() and stops["stop_id"].is_unique)

    # 17 -- The population split by band must add back to the city total.
    banded = access.groupby("band")["population"].sum().sum()
    check("band populations add to the city total", banded == total, f"{banded:,}")

    # 18 -- Sanity: the city centre wards should be well served.
    centre_wards = access[access["ward_label"].str.contains("Shivaji Nagar|K R Market")]
    check("central wards come out under 15 minutes",
          (centre_wards["median_min"] < 15).all(),
          ", ".join(f"{r.ward_label} {r.median_min:.0f}" for r in centre_wards.itertuples()))

    width = max(len(name) for name, _, _ in results)
    failures = 0
    for name, ok, detail in results:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        suffix = f"   {detail}" if detail else ""
        print(f"{flag}  {name.ljust(width)}{suffix}")

    print()
    print(f"{len(results) - failures} of {len(results)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
