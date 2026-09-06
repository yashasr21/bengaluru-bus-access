"""
Step 5 of 6 -- turn stop-level journey times into a number per ward.

Input : data/processed/wards.geojson, stop_access.csv, hospitals.csv
Output: data/processed/grid_points.csv
        data/processed/ward_access.csv

Why sample instead of using the ward centroid
    Wards here run from 0.32 sq km to 29.6 sq km. A centroid tells you about
    one spot in the middle, which for Hemmigepura is a field. Instead the ward
    is covered with a 250 m grid and every point is routed separately. The
    ward's headline number is the median of its points, so it describes the
    typical resident rather than the luckiest or the unluckiest one.

    The mean, the best point and the worst point are all kept in the output
    as well, because the spread inside a ward is sometimes the story.

From a grid point there are two ways to reach a hospital:
    walk the whole way, if one is within 2 km
    walk up to 500 m to a bus stop, then the journey computed in step 4
The better of the two wins.

Three sensitivity runs are computed alongside the headline, so that the
write-up can say how much the answer moves when an assumption changes:
    catchment at 800 m instead of 500 m
    only routes running every 30 minutes or better
    only hospitals that treat more than one kind of illness
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

from settings import (
    BAND_COLOURS,
    CATCHMENT_M,
    CRS_METRIC,
    GRID_SPACING_M,
    MAX_JOURNEY_MIN,
    PROCESSED,
    WALK_SPEED_M_PER_MIN,
    band_for,
)

# Nobody walks 6 km to hospital, but plenty of people walk two.
MAX_WALK_ALL_THE_WAY_M = 2000

WIDE_CATCHMENT_M = 800


def build_grid(wards):
    """Regular points inside the wards, tagged with the ward they fall in."""
    minx, miny, maxx, maxy = wards.total_bounds
    xs = np.arange(minx + GRID_SPACING_M / 2, maxx, GRID_SPACING_M)
    ys = np.arange(miny + GRID_SPACING_M / 2, maxy, GRID_SPACING_M)
    mesh_x, mesh_y = np.meshgrid(xs, ys)
    points = gpd.GeoDataFrame(
        geometry=[Point(x, y) for x, y in zip(mesh_x.ravel(), mesh_y.ravel())],
        crs=CRS_METRIC,
    )
    tagged = gpd.sjoin(points, wards[["ward_no", "ward_label", "geometry"]], how="inner")
    tagged = tagged.drop(columns="index_right").reset_index(drop=True)

    # A ward smaller than the grid spacing can end up with no point at all.
    # Give those wards their centroid so no ward silently disappears.
    missing = set(wards.ward_no) - set(tagged.ward_no)
    if missing:
        extra = wards[wards.ward_no.isin(missing)].copy()
        extra["geometry"] = extra.geometry.representative_point()
        extra = extra[["ward_no", "ward_label", "geometry"]]
        tagged = pd.concat([tagged, extra], ignore_index=True)
        print(f"  {len(missing)} ward(s) too small for the grid, using a "
              "representative point instead")
    return gpd.GeoDataFrame(tagged, crs=CRS_METRIC)


def journeys_from_points(xy, stop_xy, stop_cost, hosp_tree, catchment_m):
    """Best time from each point: walk all the way, or walk to a stop and ride."""
    result = np.full(len(xy), np.inf)

    walk_dist, _ = hosp_tree.query(xy)
    walk_only = np.where(
        walk_dist <= MAX_WALK_ALL_THE_WAY_M, walk_dist / WALK_SPEED_M_PER_MIN, np.inf
    )
    result = np.minimum(result, walk_only)

    stop_tree = cKDTree(stop_xy)
    nearby = stop_tree.query_ball_point(xy, r=catchment_m)
    for i, stop_ids in enumerate(nearby):
        if not stop_ids:
            continue
        ids = np.asarray(stop_ids)
        walk = np.hypot(
            stop_xy[ids, 0] - xy[i, 0], stop_xy[ids, 1] - xy[i, 1]
        ) / WALK_SPEED_M_PER_MIN
        total = walk + stop_cost[ids]
        best = total.min()
        if best < result[i]:
            result[i] = best
    return result


def main():
    wards = gpd.read_file(PROCESSED / "wards.geojson").to_crs(CRS_METRIC)
    stops = pd.read_csv(PROCESSED / "stop_access.csv", dtype={"stop_id": "string"})
    hospitals = pd.read_csv(PROCESSED / "hospitals.csv")

    grid = build_grid(wards)
    xy = np.column_stack([grid.geometry.x.to_numpy(), grid.geometry.y.to_numpy()])
    print(f"sample points: {len(grid):,} across {grid.ward_no.nunique()} wards")

    stop_xy = stops[["easting", "northing"]].to_numpy()
    hosp_tree = cKDTree(hospitals[["easting", "northing"]].to_numpy())
    general = hospitals[~hospitals["single_specialty"]]
    gen_tree = cKDTree(general[["easting", "northing"]].to_numpy())

    def cost_column(name):
        return stops[name].fillna(np.inf).to_numpy()

    print("routing the grid ...")
    grid["minutes"] = journeys_from_points(
        xy, stop_xy, cost_column("best_min"), hosp_tree, CATCHMENT_M
    )
    grid["minutes_direct_only"] = journeys_from_points(
        xy, stop_xy, cost_column("direct_min"), hosp_tree, CATCHMENT_M
    )
    grid["minutes_800m"] = journeys_from_points(
        xy, stop_xy, cost_column("best_min"), hosp_tree, WIDE_CATCHMENT_M
    )
    grid["minutes_frequent"] = journeys_from_points(
        xy, stop_xy, cost_column("best_min_frequent_routes"), hosp_tree, CATCHMENT_M
    )
    grid["minutes_general"] = journeys_from_points(
        xy, stop_xy, cost_column("best_min_general_hospitals"), gen_tree, CATCHMENT_M
    )

    straight, nearest = hosp_tree.query(xy)
    grid["straight_line_km"] = straight / 1000.0

    for column in [
        "minutes",
        "minutes_direct_only",
        "minutes_800m",
        "minutes_frequent",
        "minutes_general",
    ]:
        grid[column] = grid[column].replace(np.inf, np.nan)
        grid.loc[grid[column] > MAX_JOURNEY_MIN, column] = np.nan

    grid_out = grid.drop(columns="geometry").copy()
    grid_out["easting"] = xy[:, 0]
    grid_out["northing"] = xy[:, 1]
    grid_out.to_csv(PROCESSED / "grid_points.csv", index=False)

    # ---------------------------------------------------------- ward rollup --
    # A point with no journey at all is not dropped before taking the median.
    # Dropping it would quietly reward the worst wards: throw away the corners
    # nobody can leave and the survivors look fine. Unreachable points are
    # charged the ceiling instead, so a ward where most points cannot reach a
    # hospital ends up with a median at the ceiling, which is the truth.
    def summarise(block):
        filled = block["minutes"].fillna(MAX_JOURNEY_MIN)
        good = block["minutes"].dropna()
        return pd.Series(
            {
                "sample_points": len(block),
                "points_reachable": len(good),
                "median_min": filled.median(),
                "mean_min": filled.mean(),
                "best_min": good.min() if len(good) else np.nan,
                "worst_min": good.max() if len(good) else np.nan,
                "share_under_30": (filled < 30).sum() / len(block),
                "median_direct_only": block["minutes_direct_only"].fillna(MAX_JOURNEY_MIN).median(),
                "median_800m": block["minutes_800m"].fillna(MAX_JOURNEY_MIN).median(),
                "median_frequent": block["minutes_frequent"].fillna(MAX_JOURNEY_MIN).median(),
                "median_general": block["minutes_general"].fillna(MAX_JOURNEY_MIN).median(),
                "straight_line_km": block["straight_line_km"].median(),
            }
        )

    rolled = grid.groupby("ward_no").apply(summarise, include_groups=False).reset_index()

    wards_flat = wards.drop(columns="geometry")
    result = wards_flat.merge(rolled, on="ward_no", how="left")
    result["share_reachable"] = result["points_reachable"] / result["sample_points"]
    result["band"] = result["median_min"].map(band_for)
    result["band_colour"] = result["band"].map(BAND_COLOURS)
    result["people_over_45"] = np.where(
        result["median_min"] >= 45, result["population"], 0
    )
    result["people_over_60"] = np.where(
        (result["median_min"] >= 60) | result["median_min"].isna(), result["population"], 0
    )

    # How much slower is the bus than a crow flying there? A ward that is close
    # to a hospital but takes an hour to reach it is the interesting case.
    result["crow_fly_min"] = result["straight_line_km"] * 1000 / WALK_SPEED_M_PER_MIN
    result["penalty_ratio"] = result["median_min"] / result["crow_fly_min"]

    result = result.sort_values("median_min", na_position="last").reset_index(drop=True)
    result.to_csv(PROCESSED / "ward_access.csv", index=False)

    total_pop = result["population"].sum()
    print()
    print(f"wards scored          : {len(result)}")
    print(f"median ward journey   : {result['median_min'].median():.0f} min")
    print(f"people over 45 min    : {result['people_over_45'].sum():,} "
          f"({result['people_over_45'].sum() / total_pop:.1%})")
    print(f"people over 60 min    : {result['people_over_60'].sum():,} "
          f"({result['people_over_60'].sum() / total_pop:.1%})")
    print()
    print(result["band"].value_counts().to_string())
    print()
    print("worst five wards")
    print(result.tail(5)[["ward_label", "median_min", "population"]].to_string(index=False))
    print()
    print("best five wards")
    print(result.head(5)[["ward_label", "median_min", "population"]].to_string(index=False))


if __name__ == "__main__":
    main()
