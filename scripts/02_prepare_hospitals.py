"""
Step 2 of 6 -- the hospital list, and the rule for what counts as one.

Input : data/raw/kgis-health/*.geojson      (Karnataka GIS health layers)
        data/raw/osm_hospitals.csv          (optional, see fetch_osm_hospitals.py)
Output: data/processed/hospitals.csv
        data/processed/hospitals_dropped.csv   (what got removed and why)

This was the fiddliest part of the project and the part with the most
judgement in it, so the rule is written down rather than left in the code.

WHAT COUNTS AS A HOSPITAL HERE
    In: facilities that admit patients overnight or run an emergency room --
        district hospitals, taluk hospitals, community health centres,
        tertiary centres, specialty hospitals, teaching hospitals attached to
        medical colleges, trauma centres, ENT hospitals.
    Out: primary health centres and urban PHCs (outpatient, daytime),
        sub-centres, wellness centres, standalone labs, scanning centres,
        pharmacies, ambulance parking points, training institutes.

A primary health centre is a real and useful thing. It is not where you go at
2 a.m. with a broken arm, and this project is about the 2 a.m. question.

I wanted to weight hospitals by bed count so that a 900-bed teaching hospital
did not count the same as a 30-bed community centre. The BedCount column
exists in the KGIS layers and is zero for every single row, so that idea died.
The fallback rule is the facility type above: every facility in the list is
treated as one hospital, and a journey ends when you reach any of them.

The KGIS layers cover government facilities. Bengaluru's private hospitals are
not in them. That is a genuine limitation and it is stated in the README, not
hidden. If you run fetch_osm_hospitals.py first, the OpenStreetMap points get
merged in here and the private side is covered too.
"""

import json
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from settings import CRS_LATLON, CRS_METRIC, PROCESSED, RAW

KGIS_DIR = RAW / "kgis-health"
OSM_FILE = RAW / "osm_hospitals.csv"

# layer file -> (facility type used in the output, name column suffix)
INCLUDE = {
    "District Hospital.geojson": ("District hospital", "DHOName"),
    "Taluk Hospital.geojson": ("Taluk hospital", "THOName"),
    "Community Health Center.geojson": ("Community health centre", "CHCName"),
    "Tertiary Health Center.geojson": ("Tertiary centre", "THCName"),
    "Specialty Hospital.geojson": ("Specialty hospital", "SHOName"),
    "Medical College.geojson": ("Teaching hospital", "MCOName"),
    "Trauma Centre.geojson": ("Trauma centre", "TRCName"),
    "ENT Hospital.geojson": ("ENT hospital", "ENT_HospitalName"),
}

# Everything outside BBMP is dropped, but a hospital just over the boundary is
# still a hospital you can catch a bus to, so keep a ring around the city.
EDGE_BUFFER_M = 3000


def tidy_name(raw):
    """KGIS names arrive in a mix of shouting, spacing and abbreviation."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return ""
    s = str(raw).strip()
    s = re.sub(r"\s+", " ", s)
    if s.isupper():
        s = s.title()
    s = s.replace("Hosp.", "Hospital").replace("Govt.", "Government")
    s = s.replace("Ghosp", "Government Hospital")
    return s


# Words that carry no information about *which* hospital this is. The place
# names matter here: KGIS writes the same hospital as "Victoria Hospital" in
# one layer and "Victoria Hospital, Bengaluru Urban" in another.
NOISE_WORDS = {
    "the", "hospital", "hospitals", "government", "govt", "general", "centre",
    "center", "and", "of", "dr", "sri", "shri", "pvt", "ltd", "bengaluru",
    "bangalore", "urban", "rural", "north", "south", "east", "west",
    "research", "institute", "medical",
}

# A hospital that only treats one kind of illness is still a hospital, but you
# cannot take a broken wrist to a cancer institute. Flagged so the sensitivity
# check in step 5 can rerun the whole thing without them.
SINGLE_SPECIALTY_HINTS = (
    "oncology", "cardio", "chest disease", "leprosy", "nephro", "urology",
    "heart foundation", "dental", "ent ", "eye", "child health", "maternity",
)


def name_tokens(name):
    """Loose token set for spotting the same hospital written two ways."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return {w for w in s.split() if w not in NOISE_WORDS and len(w) > 2}


def looks_single_specialty(name):
    low = " " + name.lower() + " "
    return any(hint in low for hint in SINGLE_SPECIALTY_HINTS)


def load_kgis():
    rows = []
    for filename, (facility_type, name_field) in INCLUDE.items():
        path = KGIS_DIR / filename
        if not path.exists():
            print(f"  ! missing layer {filename}")
            continue
        blob = json.loads(path.read_text())
        for feature in blob["features"]:
            geom = feature.get("geometry") or {}
            if geom.get("type") != "Point":
                continue
            lon, lat = geom["coordinates"][:2]
            props = {k.split(".")[-1]: v for k, v in feature["properties"].items()}
            # Kept only to prove the column is empty; see quality_checks.py
            beds = props.get("BedCount")
            try:
                beds = float(beds)
            except (TypeError, ValueError):
                beds = np.nan
            rows.append(
                {
                    "name": tidy_name(props.get(name_field) or props.get("FacilityName")),
                    "facility_type": facility_type,
                    "beds": beds if beds and beds > 0 else np.nan,
                    "source": "KGIS",
                    "lon": lon,
                    "lat": lat,
                }
            )
    return pd.DataFrame(rows)


def load_osm():
    if not OSM_FILE.exists():
        return pd.DataFrame(columns=["name", "facility_type", "beds", "source", "lon", "lat"])
    osm = pd.read_csv(OSM_FILE)
    osm["name"] = osm["name"].map(tidy_name)
    osm["facility_type"] = "OSM hospital"
    osm["source"] = "OpenStreetMap"
    if "beds" not in osm:
        osm["beds"] = np.nan
    return osm[["name", "facility_type", "beds", "source", "lon", "lat"]]


def main():
    kgis = load_kgis()
    osm = load_osm()
    hospitals = pd.concat([kgis, osm], ignore_index=True)
    print(f"raw candidate rows      : {len(hospitals)}  "
          f"(KGIS {len(kgis)}, OSM {len(osm)})")

    dropped = []

    # -- drop rows with no usable name or a nonsense coordinate ---------------
    bad_coords = (
        hospitals["lat"].isna()
        | hospitals["lon"].isna()
        | ~hospitals["lat"].between(-90, 90)
        | ~hospitals["lon"].between(-180, 180)
    )
    for _, row in hospitals[bad_coords].iterrows():
        dropped.append({"name": row["name"], "reason": "bad coordinate"})
    hospitals = hospitals[~bad_coords].copy()

    blank = hospitals["name"].str.len() < 3
    for _, row in hospitals[blank].iterrows():
        dropped.append({"name": row["name"], "reason": "no usable name"})
    hospitals = hospitals[~blank].copy()

    # -- clip to BBMP plus a ring -------------------------------------------
    gdf = gpd.GeoDataFrame(
        hospitals,
        geometry=[Point(x, y) for x, y in zip(hospitals.lon, hospitals.lat)],
        crs=CRS_LATLON,
    ).to_crs(CRS_METRIC)

    outline = gpd.read_file(PROCESSED / "bbmp_outline.geojson").to_crs(CRS_METRIC)
    catchment = outline.geometry.iloc[0].buffer(EDGE_BUFFER_M)
    inside = gdf.geometry.within(catchment)
    for _, row in gdf[~inside].iterrows():
        dropped.append({"name": row["name"], "reason": "outside Bengaluru"})
    gdf = gdf[inside].copy()
    print(f"inside BBMP + {EDGE_BUFFER_M // 1000} km ring: {len(gdf)}")

    # -- de-duplicate --------------------------------------------------------
    # Two passes, because the data fails in two different ways. Some rows are
    # the same hospital listed in two layers at almost the same point; others
    # are the same hospital with slightly different names 40 m apart.
    gdf["easting"] = gdf.geometry.x
    gdf["northing"] = gdf.geometry.y
    gdf["tokens"] = gdf["name"].map(name_tokens)

    # rank so that when duplicates collapse, the richer row survives
    type_rank = {
        "Teaching hospital": 0,
        "District hospital": 1,
        "Specialty hospital": 2,
        "Tertiary centre": 3,
        "Taluk hospital": 4,
        "Trauma centre": 5,
        "Community health centre": 6,
        "ENT hospital": 7,
        "OSM hospital": 8,
    }
    gdf["rank"] = gdf["facility_type"].map(type_rank).fillna(9)
    gdf = gdf.sort_values(["rank", "beds"], ascending=[True, False]).reset_index(drop=True)

    keep_mask = np.ones(len(gdf), dtype=bool)
    coords = gdf[["easting", "northing"]].to_numpy()
    tokens = list(gdf["tokens"])
    names = gdf["name"].to_numpy()

    SAME_SITE_M = 120     # one campus, one bus stop, one destination
    SAME_NAME_M = 800     # same name a street apart is the same hospital

    for i in range(len(gdf)):
        if not keep_mask[i]:
            continue
        dx = coords[:, 0] - coords[i, 0]
        dy = coords[:, 1] - coords[i, 1]
        dist = np.sqrt(dx * dx + dy * dy)

        # Jaccard overlap of the meaningful words in the two names.
        overlap = np.array(
            [
                len(tokens[i] & t) / max(1, len(tokens[i] | t))
                for t in tokens
            ]
        )
        same = (dist < SAME_SITE_M) | ((overlap >= 0.5) & (dist < SAME_NAME_M))
        same[: i + 1] = False
        for j in np.where(same & keep_mask)[0]:
            why = "same site" if dist[j] < SAME_SITE_M else "same name"
            dropped.append(
                {
                    "name": names[j],
                    "reason": f"{why} as '{names[i]}' ({dist[j]:.0f} m apart)",
                }
            )
        keep_mask[same] = False

    gdf = gdf[keep_mask].copy()
    print(f"after de-duplication     : {len(gdf)}")

    # -- final table ---------------------------------------------------------
    gdf = gdf.sort_values(["facility_type", "name"]).reset_index(drop=True)
    gdf.insert(0, "hospital_id", np.arange(1, len(gdf) + 1))
    gdf["single_specialty"] = gdf["name"].map(looks_single_specialty)

    out = gdf[["hospital_id", "name", "facility_type", "single_specialty",
               "source", "lat", "lon", "easting", "northing"]].copy()
    out.to_csv(PROCESSED / "hospitals.csv", index=False)
    pd.DataFrame(dropped).to_csv(PROCESSED / "hospitals_dropped.csv", index=False)

    print()
    print(out["facility_type"].value_counts().to_string())
    known_beds = int(gdf["beds"].notna().sum())
    print(f"\nbed count known for      : {known_beds} of {len(out)} facilities"
          " (column is empty upstream, so every hospital counts equally)")
    print(f"single-specialty flagged : {int(out['single_specialty'].sum())}"
          " (cancer, cardiac, chest, kidney and similar)")
    print(f"rows dropped and logged  : {len(dropped)}")


if __name__ == "__main__":
    main()
