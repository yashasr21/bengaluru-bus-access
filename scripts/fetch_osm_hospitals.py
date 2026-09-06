"""
Optional extra step: pull hospital points from OpenStreetMap.

Run this BEFORE 02_prepare_hospitals.py and that script will merge the result
in automatically. Skip it and the analysis runs on the Karnataka health GIS
layers alone, which is how the published figures were produced.

    python fetch_osm_hospitals.py

Why it is optional
    The Karnataka layers are official and carry facility type, but they cover
    government and empanelled facilities. OpenStreetMap fills in the private
    hospitals, at the cost of uneven tagging: some entries are 900-bed
    multi-specialities and some are a dentist's front room mapped by a
    volunteer in 2014. Adding it changes the headline, so if you run this,
    say so in the README rather than quietly publishing a different number.

Overpass is a shared free service. This asks for one bounding box, once, and
writes the answer to disk so you never have to ask twice.
"""

import csv
import json
import time
import urllib.error
import urllib.request

from settings import RAW

OUT = RAW / "osm_hospitals.csv"

# A generous box around BBMP: south, west, north, east.
BBOX = (12.72, 77.35, 13.22, 77.88)

QUERY = f"""
[out:json][timeout:120];
(
  node["amenity"="hospital"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["amenity"="hospital"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["amenity"="hospital"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def fetch():
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    for attempt, url in enumerate(ENDPOINTS):
        try:
            print(f"asking {url} ...")
            request = urllib.request.Request(
                url, data=body,
                headers={"User-Agent": "bengaluru-bus-access/1.0 (portfolio project)"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"  failed: {error}")
            if attempt < len(ENDPOINTS) - 1:
                print("  waiting 20 seconds before trying the mirror")
                time.sleep(20)
    raise SystemExit(
        "Overpass did not answer. It is a free shared service and is often busy;\n"
        "try again in a few minutes, or skip this step -- the pipeline runs\n"
        "without it."
    )


def main():
    payload = fetch()
    rows = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        if not name:
            continue  # an unnamed polygon is not something you can direct anyone to
        if element["type"] == "node":
            lat, lon = element.get("lat"), element.get("lon")
        else:
            centre = element.get("center") or {}
            lat, lon = centre.get("lat"), centre.get("lon")
        if lat is None or lon is None:
            continue
        rows.append(
            {
                "name": name,
                "beds": tags.get("beds", ""),
                "operator": tags.get("operator", ""),
                "lat": lat,
                "lon": lon,
            }
        )

    RAW.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "beds", "operator", "lat", "lon"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} named hospitals written to {OUT}")
    print("Now rerun the pipeline from 02_prepare_hospitals.py.")


if __name__ == "__main__":
    main()
