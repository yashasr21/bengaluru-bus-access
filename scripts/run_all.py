"""
Run the whole pipeline in order.

    python run_all.py

Each step is a normal script that can also be run on its own, which is how I
worked on it. This just saves typing when rerunning from the top.
"""

import runpy
import sys
import time
from pathlib import Path

STEPS = [
    "00_download_data.py",
    "01_prepare_wards.py",
    "02_prepare_hospitals.py",
    "check_alignment.py",
    "03_bus_network.py",
    "04_journey_times.py",
    "05_ward_access.py",
    "06_maps.py",
    "07_build_database.py",
    "08_build_dashboard.py",
    "quality_checks.py",
]

here = Path(__file__).parent
sys.path.insert(0, str(here))

for step in STEPS:
    print("\n" + "=" * 68)
    print(step)
    print("=" * 68)
    started = time.time()
    runpy.run_path(str(here / step), run_name="__main__")
    print(f"-- {time.time() - started:.1f}s")

print("\nDone. Open docs/index.html.")
