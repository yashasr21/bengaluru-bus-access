"""
Step 6 of 6 -- the map, and the still images for the README.

Input : data/processed/wards.geojson, ward_access.csv, hospitals.csv,
        stop_access.csv
Output: docs/map.html                (standalone, opens in any browser)
        docs/dashboard_data.json     (numbers the dashboard page reads)
        maps/*.png                   (three stills)

The interactive map carries the detail. The stills exist so that the README
shows something on GitHub before anyone clicks a link, which is the point at
which most people decide whether to keep reading.
"""

import json

import folium
import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from settings import (
    BAND_COLOURS,
    CRS_LATLON,
    CRS_METRIC,
    DOCS,
    MAPS,
    MAX_JOURNEY_MIN,
    PROCESSED,
)

BAND_ORDER = ["Under 30 min", "30 to 45 min", "45 to 60 min", "Over 60 min", "Unreachable"]


def load():
    wards = gpd.read_file(PROCESSED / "wards.geojson").to_crs(CRS_METRIC)
    access = pd.read_csv(PROCESSED / "ward_access.csv")
    hospitals = pd.read_csv(PROCESSED / "hospitals.csv")
    stops = pd.read_csv(PROCESSED / "stop_access.csv", dtype={"stop_id": "string"})
    merged = wards.merge(
        access.drop(columns=[c for c in ["ward_label", "population", "area_sqkm",
                                         "density_per_sqkm", "ward_name"]
                             if c in access.columns and c in wards.columns]),
        on="ward_no",
        how="left",
    )
    return merged, hospitals, stops


def build_interactive(wards, hospitals, stops):
    # Centroid in metres first, then converted, otherwise geopandas warns that
    # averaging degrees is meaningless. It is right to warn.
    centre_metric = wards.geometry.union_all().centroid
    centre_point = (
        gpd.GeoSeries([centre_metric], crs=CRS_METRIC).to_crs(CRS_LATLON).iloc[0]
    )
    latlon = wards.to_crs(CRS_LATLON)

    # Plain OpenStreetMap tiles. The Carto basemap looks better but started
    # asking for an API key, and a map that needs a key is a map that breaks
    # for whoever opens the repo next.
    fmap = folium.Map(
        location=[centre_point.y, centre_point.x],
        zoom_start=11,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    def style(feature):
        return {
            "fillColor": feature["properties"]["band_colour"] or "#4a4a55",
            "color": "#ffffff",
            "weight": 0.7,
            "fillOpacity": 0.78,
        }

    fields = ["ward_label", "band", "median_min", "population", "straight_line_km"]
    aliases = ["Ward", "Band", "Typical journey (min)", "Population (2011)",
               "Straight line to nearest hospital (km)"]

    show = latlon.copy()
    show["median_min"] = show["median_min"].round(0)
    show["straight_line_km"] = show["straight_line_km"].round(1)

    folium.GeoJson(
        show,
        name="Wards by bus journey time",
        style_function=style,
        highlight_function=lambda _: {"weight": 2.5, "color": "#111111"},
        tooltip=folium.GeoJsonTooltip(fields=fields, aliases=aliases, sticky=True),
    ).add_to(fmap)

    hospital_layer = folium.FeatureGroup(name="Hospitals", show=True)
    for _, row in hospitals.iterrows():
        folium.CircleMarker(
            [row.lat, row.lon],
            radius=4,
            color="#111111",
            weight=1,
            fill=True,
            fill_color="#e6e6e6",
            fill_opacity=0.95,
            popup=folium.Popup(f"<b>{row['name']}</b><br>{row.facility_type}", max_width=260),
        ).add_to(hospital_layer)
    hospital_layer.add_to(fmap)

    # Bus stops go on as a layer that starts switched off. Nine and a half
    # thousand markers make the map unreadable if they are on by default, but
    # being able to flick them on is the fastest way to see why a ward is red:
    # in Varthur the stops are there, they just do not go anywhere useful.
    stop_features = []
    for row in stops.itertuples():
        journey = (
            f"{row.best_min:.0f} min to {row.nearest_hospital}"
            if pd.notna(row.best_min)
            else "no bus journey to a hospital"
        )
        stop_features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point",
                             "coordinates": [round(row.stop_lon, 5), round(row.stop_lat, 5)]},
                "properties": {"stop": row.stop_name, "journey": journey},
            }
        )

    # One GeoJSON layer rather than 9,681 separate marker objects. The marker
    # version worked and produced a 10 MB page; this one is under 2 MB and
    # scrolls smoothly on a phone.
    folium.GeoJson(
        {"type": "FeatureCollection", "features": stop_features},
        name=f"BMTC stops ({len(stops):,})",
        show=False,
        marker=folium.CircleMarker(
            radius=2, weight=0, fill=True, fill_color="#2d5c9e", fill_opacity=0.55
        ),
        tooltip=folium.GeoJsonTooltip(fields=["stop", "journey"],
                                      aliases=["Stop", "Nearest hospital"]),
    ).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)

    swatches = "".join(
        f'<div style="margin:2px 0"><span style="display:inline-block;width:14px;'
        f'height:14px;background:{BAND_COLOURS[b]};border:1px solid #333;'
        f'vertical-align:middle"></span>&nbsp;{b}</div>'
        for b in BAND_ORDER
    )
    legend = f"""
    <div style="position:fixed;bottom:24px;left:24px;z-index:9999;background:#fff;
                padding:12px 14px;border:1px solid #999;border-radius:6px;
                font:12px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;
                box-shadow:0 2px 8px rgba(0,0,0,.2)">
      <div style="font-weight:700;margin-bottom:6px">Typical bus journey<br>to a hospital</div>
      {swatches}
      <div style="margin-top:8px;color:#555;max-width:200px">
        Median of 250 m sample points in the ward. Scheduled times, not observed.
      </div>
    </div>"""
    fmap.get_root().html.add_child(folium.Element(legend))

    DOCS.mkdir(parents=True, exist_ok=True)
    fmap.save(DOCS / "map.html")
    print(f"wrote {DOCS / 'map.html'}")


def build_stills(wards, hospitals, stops):
    MAPS.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"

    # --- 1. the choropleth --------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 9.6))
    for band in BAND_ORDER:
        subset = wards[wards["band"] == band]
        if len(subset):
            subset.plot(ax=ax, color=BAND_COLOURS[band], edgecolor="white", linewidth=0.5)
    hospitals_xy = hospitals[["easting", "northing"]].to_numpy()
    ax.scatter(hospitals_xy[:, 0], hospitals_xy[:, 1], s=18, c="#101018",
               edgecolor="white", linewidth=0.6, zorder=5, label="Hospital")
    ax.set_axis_off()
    ax.set_title(
        "Typical bus journey to a hospital, BBMP wards\n"
        "median of 250 m sample points, scheduled BMTC timetable",
        fontsize=13, loc="left", pad=14,
    )
    handles = [mpatches.Patch(color=BAND_COLOURS[b], label=b) for b in BAND_ORDER
               if (wards["band"] == b).any()]
    handles.append(plt.Line2D([], [], marker="o", color="none",
                              markerfacecolor="#101018", markeredgecolor="white",
                              markersize=7, label="Hospital"))
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(MAPS / "ward_journey_bands.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 2. where the buses and the hospitals are ---------------------------
    fig, ax = plt.subplots(figsize=(9, 9.6))
    wards.boundary.plot(ax=ax, color="#c9c9d1", linewidth=0.5)
    ax.scatter(stops["easting"], stops["northing"], s=0.8, c="#3d6fb5", alpha=0.35,
               label=f"BMTC stop ({len(stops):,})")
    ax.scatter(hospitals_xy[:, 0], hospitals_xy[:, 1], s=44, c="#c0392b",
               edgecolor="white", linewidth=0.8, zorder=5,
               label=f"Hospital ({len(hospitals)})")
    ax.set_axis_off()
    ax.set_title("Bus stops and hospitals\nthe stops are everywhere, the hospitals are not",
                 fontsize=13, loc="left", pad=14)
    ax.legend(loc="lower left", frameon=False, fontsize=9, markerscale=2)
    fig.tight_layout()
    fig.savefig(MAPS / "stops_and_hospitals.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- 3. the worst served wards -----------------------------------------
    worst = wards.dropna(subset=["median_min"]).nlargest(15, "median_min")
    worst = worst.sort_values("median_min")
    fig, ax = plt.subplots(figsize=(9, 6.4))
    colours = [BAND_COLOURS[b] for b in worst["band"]]
    ax.barh(worst["ward_label"], worst["median_min"], color=colours, edgecolor="#2a2a33")
    for y, (value, pop) in enumerate(zip(worst["median_min"], worst["population"])):
        ax.text(value + 1.5, y, f"{value:.0f} min  ·  {pop:,} people",
                va="center", fontsize=8.5, color="#333")
    ax.set_xlabel("Typical journey to a hospital by bus (minutes)")
    ax.set_xlim(0, worst["median_min"].max() * 1.42)
    ax.set_title("The fifteen worst served wards", fontsize=13, loc="left", pad=12)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(MAPS / "worst_served_wards.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"wrote 3 stills to {MAPS}")


def build_dashboard_data(wards, hospitals, stops):
    access = pd.read_csv(PROCESSED / "ward_access.csv")
    patterns = pd.read_csv(PROCESSED / "patterns_summary.csv")
    total_pop = int(access["population"].sum())

    def pop_where(mask):
        return int(access.loc[mask, "population"].sum())

    bands = []
    for band in BAND_ORDER:
        rows = access[access["band"] == band]
        if len(rows) == 0:
            continue
        bands.append(
            {
                "band": band,
                "wards": int(len(rows)),
                "population": int(rows["population"].sum()),
                "share": round(rows["population"].sum() / total_pop * 100, 1),
                "colour": BAND_COLOURS[band],
            }
        )

    def table(frame, columns):
        return frame[columns].round(1).to_dict("records")

    worst = access.nlargest(12, "median_min")
    best = access.nsmallest(12, "median_min")
    close_but_slow = (
        access[access["straight_line_km"] < 4].nlargest(10, "penalty_ratio")
    )
    far_but_fine = access[access["straight_line_km"] > 4].nsmallest(10, "median_min")

    scatter = access[["ward_label", "straight_line_km", "median_min", "population",
                      "band_colour"]].copy()

    payload = {
        "generated_from": {
            "gtfs": "BMTC unofficial GTFS, feed version 20260712",
            "wards": "BBMP 2022 delimitation ward layer, Census 2011 population",
            "hospitals": "Karnataka health GIS facility layers",
        },
        "headline": {
            "population": total_pop,
            "wards": int(len(access)),
            "hospitals": int(len(hospitals)),
            "stops": int(len(stops)),
            "routes": int(patterns["route_id"].nunique()),
            "trips": int(patterns["n_trips"].sum()),
            "city_median_min": round(float(access["median_min"].median()), 1),
            "pop_under_30": pop_where(access["median_min"] < 30),
            "pop_over_45": pop_where(access["median_min"] >= 45),
            "pop_over_60": pop_where(access["median_min"] >= 60),
            "wards_over_45": int((access["median_min"] >= 45).sum()),
            "stops_near_hospital": int((stops["metres_to_hospital"] <= 500).sum()),
            "share_stops_needing_change": round(float(stops["needs_change"].mean()) * 100, 1),
            "frequent_patterns_share": round(
                float((patterns["headway_min"] <= 30).mean()) * 100, 1
            ),
        },
        "bands": bands,
        "worst": table(worst, ["ward_label", "median_min", "population", "straight_line_km"]),
        "best": table(best, ["ward_label", "median_min", "population", "straight_line_km"]),
        "close_but_slow": table(
            close_but_slow,
            ["ward_label", "median_min", "straight_line_km", "penalty_ratio", "population"],
        ),
        "far_but_fine": table(
            far_but_fine, ["ward_label", "median_min", "straight_line_km", "population"]
        ),
        "scatter": scatter.round(2).to_dict("records"),
        "sensitivity": [
            {
                "label": label,
                "population_over_45": pop_where(access[column] >= 45),
                "wards_over_45": int((access[column] >= 45).sum()),
                "city_median": round(float(access[column].median()), 1),
            }
            for label, column in [
                ("Headline: 500 m walk, every route, every hospital", "median_min"),
                ("Walk up to 800 m to a stop", "median_800m"),
                ("Only routes every 30 min or better", "median_frequent"),
                ("Only hospitals treating more than one illness", "median_general"),
                ("No changing buses", "median_direct_only"),
            ]
        ],
        "facility_mix": [
            {"type": key, "count": int(value)}
            for key, value in hospitals["facility_type"].value_counts().items()
        ],
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "dashboard_data.json").write_text(json.dumps(payload, indent=1))
    print(f"wrote {DOCS / 'dashboard_data.json'}")


def main():
    wards, hospitals, stops = load()
    build_interactive(wards, hospitals, stops)
    build_stills(wards, hospitals, stops)
    build_dashboard_data(wards, hospitals, stops)


if __name__ == "__main__":
    main()
