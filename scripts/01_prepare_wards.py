"""
Step 1 of 6 -- ward boundaries and ward population.

Input : data/raw/bbmp-wards.json
Output: data/processed/wards.geojson   (metric CRS, cleaned attributes)
        data/processed/wards.csv       (no geometry, for the SQL side)

The raw file is the ward layer published for the BBMP 2022 delimitation
exercise. It is unusual and very useful: the boundaries and the ward
population sit in the same file, so I did not have to guess at a join between
a shapefile and a census table. Ward population there is the Census 2011
count, which is what BBMP used to draw the wards.
"""

import json

import geopandas as gpd
import pandas as pd

from settings import CRS_METRIC, PROCESSED, RAW

SOURCE = RAW / "bbmp-wards.json"


def main():
    wards = gpd.read_file(SOURCE)

    # The file declares EPSG:32643 in its crs block, but geopandas does not
    # always pick that up from a plain GeoJSON, so set it explicitly.
    if wards.crs is None:
        wards = wards.set_crs(CRS_METRIC)
    wards = wards.to_crs(CRS_METRIC)

    keep = wards[["id", "name_en", "ward_name_en", "population", "geometry"]].copy()
    keep = keep.rename(
        columns={"id": "ward_no", "name_en": "ward_name", "ward_name_en": "ward_label"}
    )
    keep["ward_no"] = keep["ward_no"].astype(int)
    keep["population"] = keep["population"].astype(int)

    # Area computed from the geometry rather than trusted from the file's own
    # ward_area column. They agree to about a percent, which was a small relief.
    keep["area_sqkm"] = keep.geometry.area / 1_000_000
    keep["density_per_sqkm"] = keep["population"] / keep["area_sqkm"]

    # Fix any self-intersecting rings before the spatial joins later on.
    bad = (~keep.geometry.is_valid).sum()
    if bad:
        print(f"  repairing {bad} invalid ward polygons")
        keep["geometry"] = keep.geometry.buffer(0)

    keep = keep.sort_values("ward_no").reset_index(drop=True)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    keep.to_file(PROCESSED / "wards.geojson", driver="GeoJSON")
    keep.drop(columns="geometry").to_csv(PROCESSED / "wards.csv", index=False)

    # A single dissolved outline of BBMP. Used to clip hospitals and to build
    # the sampling grid, so it is worth saving once instead of redoing it.
    outline = gpd.GeoDataFrame(
        {"name": ["BBMP"]}, geometry=[keep.geometry.union_all()], crs=CRS_METRIC
    )
    outline.to_file(PROCESSED / "bbmp_outline.geojson", driver="GeoJSON")

    print(f"wards           : {len(keep)}")
    print(f"population total: {keep['population'].sum():,}")
    print(f"area total      : {keep['area_sqkm'].sum():.1f} sq km")
    print(f"smallest ward   : {keep.loc[keep.area_sqkm.idxmin(), 'ward_label']}"
          f" ({keep.area_sqkm.min():.2f} sq km)")
    print(f"largest ward    : {keep.loc[keep.area_sqkm.idxmax(), 'ward_label']}"
          f" ({keep.area_sqkm.max():.2f} sq km)")


if __name__ == "__main__":
    main()
