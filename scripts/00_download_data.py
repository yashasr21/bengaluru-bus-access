"""
Step 0 -- fetch the three raw datasets.

    python 00_download_data.py

Downloads about 45 MB and unzips the GTFS feed to roughly 200 MB. Everything
lands in data/raw/ and nothing here is committed to the repository, so this is
the first thing to run on a fresh clone.

Where the data comes from, and why these sources
    Buses      github.com/Vonter/bmtc-gtfs
               An unofficial GTFS build of the BMTC network, scraped from the
               Namma BMTC app. BMTC does not publish an official feed, so this
               is the only machine-readable timetable there is. The publisher
               is clear that app timings are approximate; see the limitations
               in the README.

    Wards      github.com/statsofindia/bbmp-delimitation-2022
               The ward layer prepared for the 2022 BBMP delimitation. It
               carries the Census 2011 population inside the same file as the
               boundary, which removes the most error-prone join in the
               project.

    Hospitals  github.com/Vonter/karnataka-social-services-data
               Health facility layers scraped from the Karnataka GIS portal
               (KGIS / KSRSAC). Only the layers that describe places with
               inpatient or emergency care are downloaded.
"""

import io
import urllib.parse
import urllib.request
import zipfile

from settings import RAW

GTFS_ZIP = "https://raw.githubusercontent.com/Vonter/bmtc-gtfs/main/gtfs/bmtc.zip"
WARDS = ("https://raw.githubusercontent.com/statsofindia/"
         "bbmp-delimitation-2022/main/bbmp-wards.json")
KGIS_BASE = ("https://raw.githubusercontent.com/Vonter/"
             "karnataka-social-services-data/master/data/Health")

KGIS_LAYERS = [
    "Health and Family Welfare/District Hospital.geojson",
    "Health and Family Welfare/Taluk Hospital.geojson",
    "Health and Family Welfare/Community Health Center.geojson",
    "Health and Family Welfare/Tertiary Health Center.geojson",
    "Health and Family Welfare/Trauma Centre.geojson",
    "Health and Family Welfare/ENT Hospital.geojson",
    "Medical Education/Medical College.geojson",
    "Medical Education/Specialty Hospital.geojson",
]


def get(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"  have  {destination.name}")
        return
    with urllib.request.urlopen(url, timeout=180) as response:
        destination.write_bytes(response.read())
    print(f"  got   {destination.name}  ({destination.stat().st_size / 1024:,.0f} KB)")


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    print("ward boundaries and population")
    get(WARDS, RAW / "bbmp-wards.json")

    print("health facility layers")
    for layer in KGIS_LAYERS:
        url = f"{KGIS_BASE}/{urllib.parse.quote(layer)}"
        get(url, RAW / "kgis-health" / layer.split("/")[-1])

    print("BMTC GTFS feed")
    zip_path = RAW / "bmtc-gtfs.zip"
    get(GTFS_ZIP, zip_path)
    gtfs_dir = RAW / "gtfs"
    if not (gtfs_dir / "stop_times.txt").exists():
        with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as archive:
            archive.extractall(gtfs_dir)
        print(f"  unzipped {len(list(gtfs_dir.glob('*.txt')))} files to {gtfs_dir}")
    else:
        print("  already unzipped")

    print("\nready. Next: python 01_prepare_wards.py")


if __name__ == "__main__":
    main()
