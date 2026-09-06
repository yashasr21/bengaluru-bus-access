"""
Every number that the analysis depends on lives here.

I put these in one file on purpose. Halfway through building this I changed the
walking speed and then could not remember which scripts I had already fixed.
One file, one place to change.

Distances are in metres, times in minutes.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
MAPS = ROOT / "maps"

# Bengaluru sits in UTM zone 43 North. Working in this projection means a
# distance of "500" really is 500 metres on the ground. Doing the same sums in
# degrees would stretch things badly. The BBMP ward file already arrives in
# this projection, which is partly why I picked it.
CRS_METRIC = "EPSG:32643"
CRS_LATLON = "EPSG:4326"

# ---------------------------------------------------------------- walking ---
# 4.8 km/h is the usual planning figure for an adult walking on a footpath.
# It is generous for Bengaluru, where footpaths are often missing. Noted as a
# limitation rather than fudged.
WALK_SPEED_KMPH = 4.8
WALK_SPEED_M_PER_MIN = WALK_SPEED_KMPH * 1000 / 60  # 80 m/min

# Straight-line radius used as the walking catchment of a bus stop.
# 500 m at 4.8 km/h is about a six minute walk, or a ten minute walk once you
# allow for the fact that real streets are not straight.
CATCHMENT_M = 500

# Same radius on the hospital end: a stop counts as "serving" a hospital if it
# is within this distance of the hospital gate.
HOSPITAL_CATCHMENT_M = 500

# Two stops this close together are treated as the same interchange point.
# BMTC's feed carries a lot of near-duplicate stops on opposite kerbs.
TRANSFER_RADIUS_M = 150

# ------------------------------------------------------------------- buses ---
# Penalty added for making one change: getting off, crossing, finding the next
# stop, and the risk that the connection is missed.
TRANSFER_PENALTY_MIN = 8.0

# Waiting is charged as half the average headway on the route, which is what
# you would expect for a passenger who turns up without checking a timetable.
# Capped because nobody actually stands at a stop for two hours; past a point
# they check the app, call an auto, or do not travel at all.
MAX_WAIT_MIN = 20.0

# Hours of the day used to work out how often a route runs.
SERVICE_WINDOW_HOURS = 16.0  # roughly 06:00 to 22:00

# --------------------------------------------------------------- reporting ---
# Sampling grid inside each ward. 250 m keeps the smallest ward (about 0.4 km2)
# at a handful of points while staying fast enough to re-run.
GRID_SPACING_M = 250

# Anything above this is treated as unreachable rather than given a number.
# A journey this long is not a bus journey anyone makes to a hospital.
MAX_JOURNEY_MIN = 180.0

# Bands used on the map and in the write-up.
BANDS = [
    ("Under 30 min", 0, 30),
    ("30 to 45 min", 30, 45),
    ("45 to 60 min", 45, 60),
    ("Over 60 min", 60, MAX_JOURNEY_MIN),
]
BAND_COLOURS = {
    "Under 30 min": "#2e8b7a",
    "30 to 45 min": "#e8c468",
    "45 to 60 min": "#e08a4a",
    "Over 60 min": "#c0392b",
    "Unreachable": "#4a4a55",
}


def band_for(minutes):
    """Turn a journey time into one of the four bands."""
    if minutes is None or minutes != minutes or minutes >= MAX_JOURNEY_MIN:
        return "Unreachable"
    for name, low, high in BANDS:
        if low <= minutes < high:
            return name
    return "Unreachable"
