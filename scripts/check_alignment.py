"""
Phase 1 sanity check -- put all three datasets on one map before trusting any
of them.

    python check_alignment.py

Output: maps/three_layers_check.png

This runs after 01 and 02 and before anything else. The point is not to look
at the result, it is to look for the mistakes that are invisible in a table:
a layer in the wrong projection, longitude and latitude swapped, a sign flipped
so half the city ends up in the southern hemisphere. All three look perfectly
reasonable as numbers and are obvious the moment you draw them.

The checks it prints are the ones I would otherwise do by squinting:
    - do all three layers share a bounding box
    - are the coordinates plausibly Bengaluru
    - what share of stops and hospitals actually fall inside a ward
"""

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settings import CRS_LATLON, CRS_METRIC, MAPS, PROCESSED

# Bengaluru, roughly. Anything outside this box is a data problem.
EXPECTED_LON = (77.3, 77.9)
EXPECTED_LAT = (12.7, 13.3)


def main():
    wards = gpd.read_file(PROCESSED / "wards.geojson").to_crs(CRS_METRIC)
    hospitals = pd.read_csv(PROCESSED / "hospitals.csv")
    stops = pd.read_csv(PROCESSED / "stops.csv", dtype={"stop_id": "string"})

    wards_ll = wards.to_crs(CRS_LATLON)
    west, south, east, north = wards_ll.total_bounds

    print("bounding boxes in degrees")
    print(f"  wards      lon {west:.3f} to {east:.3f}   lat {south:.3f} to {north:.3f}")
    print(f"  hospitals  lon {hospitals.lon.min():.3f} to {hospitals.lon.max():.3f}"
          f"   lat {hospitals.lat.min():.3f} to {hospitals.lat.max():.3f}")
    print(f"  stops      lon {stops.stop_lon.min():.3f} to {stops.stop_lon.max():.3f}"
          f"   lat {stops.stop_lat.min():.3f} to {stops.stop_lat.max():.3f}")

    problems = []
    for label, lons, lats in [
        ("wards", np.array([west, east]), np.array([south, north])),
        ("hospitals", hospitals.lon.to_numpy(), hospitals.lat.to_numpy()),
        ("stops", stops.stop_lon.to_numpy(), stops.stop_lat.to_numpy()),
    ]:
        if lats.min() < 0:
            problems.append(f"{label}: negative latitude, southern hemisphere")
        if lons.max() < lats.max():
            problems.append(f"{label}: longitude smaller than latitude, columns look swapped")
        outside = (
            (lons < EXPECTED_LON[0]) | (lons > EXPECTED_LON[1])
            | (lats < EXPECTED_LAT[0]) | (lats > EXPECTED_LAT[1])
        ).mean()
        # Stops are allowed to spill: BMTC runs to Hosur, Nelamangala and the
        # airport, well outside BBMP. Wards and hospitals are not allowed to.
        allowance = 0.10 if label == "stops" else 0.02
        if outside > allowance:
            problems.append(f"{label}: {outside:.1%} of points outside the Bengaluru box")
        elif outside > 0.005:
            print(f"  note: {outside:.1%} of {label} sit outside the box, within tolerance")

    # How much of each point layer lands inside a ward. Stops legitimately spill
    # over the boundary because BMTC runs beyond BBMP; hospitals should not.
    outline = wards.geometry.union_all()
    hosp_points = gpd.GeoSeries(
        gpd.points_from_xy(hospitals.lon, hospitals.lat), crs=CRS_LATLON
    ).to_crs(CRS_METRIC)
    stop_points = gpd.GeoSeries(
        gpd.points_from_xy(stops.stop_lon, stops.stop_lat), crs=CRS_LATLON
    ).to_crs(CRS_METRIC)
    hosp_in = hosp_points.within(outline).mean()
    stop_in = stop_points.within(outline).mean()

    print()
    print(f"hospitals inside a BBMP ward : {hosp_in:.1%}")
    print(f"bus stops inside a BBMP ward : {stop_in:.1%}"
          "   (the rest are real: BMTC runs past the city limit)")

    if problems:
        print("\nLOOK AT THESE BEFORE GOING FURTHER")
        for problem in problems:
            print(f"  ! {problem}")
    else:
        print("\nNo alignment problems found. Draw the map anyway and look at it.")

    # ------------------------------------------------------------- the map --
    fig, ax = plt.subplots(figsize=(9, 9.4))
    wards.boundary.plot(ax=ax, color="#8f8fa6", linewidth=0.6, zorder=1)
    ax.scatter(
        stop_points.x, stop_points.y, s=1.2, c="#3d6fb5", alpha=0.35, zorder=2,
        label=f"BMTC stops ({len(stops):,})",
    )
    ax.scatter(
        hosp_points.x, hosp_points.y, s=52, c="#c0392b", edgecolor="white",
        linewidth=0.9, zorder=3, label=f"Hospitals ({len(hospitals)})",
    )
    ax.set_axis_off()
    ax.set_title(
        "Alignment check: wards, stops and hospitals on one map\n"
        "drawn before any analysis, to catch a layer in the wrong place",
        fontsize=12.5, loc="left", pad=14,
    )
    ax.legend(loc="lower left", frameon=False, fontsize=9, markerscale=2.5)
    MAPS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(MAPS / "three_layers_check.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nwrote {MAPS / 'three_layers_check.png'}")


if __name__ == "__main__":
    main()
