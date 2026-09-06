"""
Step 4 of 6 -- how long it takes to reach a hospital from each bus stop.

Input : data/processed/stops.csv, hospitals.csv, patterns.npz
Output: data/processed/stop_access.csv

The journey is built up in the order a passenger actually experiences it.

    wait for the bus        half the headway on the pattern, capped
    ride                    scheduled time between the two stops
    change, if needed       a flat 8 minute penalty, once
    walk at the far end     from the alighting stop to the hospital gate

The walk at the near end is not added here, because that depends on where in
the ward you start. Step 5 adds it.

How the search works
    Rather than routing every stop to every hospital, the problem is turned
    around and solved backwards, which is far cheaper:

    g0[stop]  cost of finishing the journey on foot from this stop.
              Infinite unless a hospital is within 500 m.
    g1[stop]  best cost using at most one bus. For each pattern, walk the
              stop list from the back keeping a running minimum of
              "time at this stop plus g0 there". Boarding at stop i then
              costs wait + (that minimum - time at i).
    g2[stop]  best cost using at most two buses. Same backward sweep, but
              the running minimum is over g1 at the alighting stop plus the
              transfer penalty.

    Each sweep touches every stop of every pattern exactly once, so the whole
    thing is linear in the size of the feed. On my laptop it runs in seconds.

A stop within 150 m of another is treated as the same interchange, because
BMTC lists the two kerbs of one road as separate stops.
"""

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from settings import (
    CATCHMENT_M,
    HOSPITAL_CATCHMENT_M,
    MAX_JOURNEY_MIN,
    MAX_WAIT_MIN,
    PROCESSED,
    TRANSFER_PENALTY_MIN,
    TRANSFER_RADIUS_M,
    WALK_SPEED_M_PER_MIN,
)

INF = np.float32(1e9)

# A pattern is called frequent if you would not wait more than half an hour.
# Used for the sensitivity run, not the headline.
FREQUENT_HEADWAY_MIN = 30.0


def backward_sweep(offsets, pattern_stops, elapsed, waits, arrive_cost, extra=0.0):
    """One pass over every pattern, from the last stop to the first.

    Returns, for each stop, the best cost of boarding there and later getting
    off somewhere with a finite arrive_cost.
    """
    best = np.full(arrive_cost.shape, INF, dtype=np.float32)
    for p in range(len(offsets) - 1):
        lo, hi = offsets[p], offsets[p + 1]
        seq = pattern_stops[lo:hi]
        times = elapsed[lo:hi]
        wait = waits[p]
        if wait >= INF:
            continue

        running = INF  # min over stops further along of (time + arrive_cost)
        for k in range(len(seq) - 1, -1, -1):
            if running < INF:
                candidate = wait + (running - times[k]) + extra
                if candidate < best[seq[k]]:
                    best[seq[k]] = candidate
            here = arrive_cost[seq[k]]
            if here < INF:
                value = times[k] + here
                if value < running:
                    running = value
    return best


def spread_to_neighbours(values, tree, coords):
    """Let a stop borrow its neighbour's cost, paying the walk between them."""
    out = values.copy()
    pairs = tree.query_ball_point(coords, r=TRANSFER_RADIUS_M)
    for i, neighbours in enumerate(pairs):
        for j in neighbours:
            if j == i:
                continue
            walk = np.hypot(*(coords[i] - coords[j])) / WALK_SPEED_M_PER_MIN
            candidate = values[j] + walk
            if candidate < out[i]:
                out[i] = candidate
    return out


def main():
    stops = pd.read_csv(PROCESSED / "stops.csv", dtype={"stop_id": "string"})
    hospitals = pd.read_csv(PROCESSED / "hospitals.csv")
    bundle = np.load(PROCESSED / "patterns.npz")

    offsets = bundle["offsets"]
    pattern_stops = bundle["stops"]
    elapsed = bundle["elapsed_min"]
    headways = bundle["headway_min"]

    stop_xy = stops[["easting", "northing"]].to_numpy()
    hosp_xy = hospitals[["easting", "northing"]].to_numpy()
    n_stops = len(stops)

    stop_tree = cKDTree(stop_xy)
    hosp_tree = cKDTree(hosp_xy)

    # -- g0: finish on foot from this stop ----------------------------------
    dist_to_hosp, nearest_hosp = hosp_tree.query(stop_xy)
    g0 = np.where(
        dist_to_hosp <= HOSPITAL_CATCHMENT_M,
        dist_to_hosp / WALK_SPEED_M_PER_MIN,
        INF,
    ).astype(np.float32)
    serving = int((g0 < INF).sum())
    print(f"stops within {HOSPITAL_CATCHMENT_M} m of a hospital: {serving:,} "
          f"of {n_stops:,} ({serving / n_stops:.1%})")

    waits = np.minimum(headways / 2.0, MAX_WAIT_MIN).astype(np.float32)

    # -- g1: at most one bus -------------------------------------------------
    print("sweeping patterns for one-bus journeys ...")
    one_bus = backward_sweep(offsets, pattern_stops, elapsed, waits, g0)
    g1 = np.minimum(g0, one_bus)
    print(f"  reachable with no change : {int((g1 < INF).sum()):,} stops")

    # -- g2: at most two buses ----------------------------------------------
    g1_nearby = spread_to_neighbours(g1, stop_tree, stop_xy)
    print("sweeping patterns for one-change journeys ...")
    two_bus = backward_sweep(
        offsets, pattern_stops, elapsed, waits, g1_nearby, extra=TRANSFER_PENALTY_MIN
    )
    g2 = np.minimum(g1, two_bus)
    print(f"  reachable with one change: {int((g2 < INF).sum()):,} stops")

    # -- sensitivity: only routes that run every 30 minutes or better --------
    frequent_waits = np.where(
        headways <= FREQUENT_HEADWAY_MIN, np.minimum(headways / 2.0, MAX_WAIT_MIN), INF
    ).astype(np.float32)
    f1 = np.minimum(g0, backward_sweep(offsets, pattern_stops, elapsed, frequent_waits, g0))
    f1_nearby = spread_to_neighbours(f1, stop_tree, stop_xy)
    f2 = np.minimum(
        f1,
        backward_sweep(
            offsets, pattern_stops, elapsed, frequent_waits, f1_nearby,
            extra=TRANSFER_PENALTY_MIN,
        ),
    )
    print(f"  same, frequent routes only: {int((f2 < INF).sum()):,} stops")

    # -- sensitivity: skip the seven single-specialty hospitals --------------
    general = hospitals[~hospitals["single_specialty"]]
    gen_tree = cKDTree(general[["easting", "northing"]].to_numpy())
    gen_dist, _ = gen_tree.query(stop_xy)
    g0_general = np.where(
        gen_dist <= HOSPITAL_CATCHMENT_M, gen_dist / WALK_SPEED_M_PER_MIN, INF
    ).astype(np.float32)
    gg1 = np.minimum(g0_general, backward_sweep(offsets, pattern_stops, elapsed, waits, g0_general))
    gg1_nearby = spread_to_neighbours(gg1, stop_tree, stop_xy)
    gg2 = np.minimum(
        gg1,
        backward_sweep(
            offsets, pattern_stops, elapsed, waits, gg1_nearby, extra=TRANSFER_PENALTY_MIN
        ),
    )

    out = stops[["stop_id", "stop_name", "easting", "northing", "stop_lat", "stop_lon"]].copy()
    out["metres_to_hospital"] = dist_to_hosp.round(0)
    out["nearest_hospital"] = hospitals["name"].to_numpy()[nearest_hosp]
    out["direct_min"] = np.where(g1 < INF, g1, np.nan).round(1)
    out["best_min"] = np.where(g2 < INF, g2, np.nan).round(1)
    out["best_min_frequent_routes"] = np.where(f2 < INF, f2, np.nan).round(1)
    out["best_min_general_hospitals"] = np.where(gg2 < INF, gg2, np.nan).round(1)
    out["needs_change"] = (g1 >= INF) & (g2 < INF)

    out.to_csv(PROCESSED / "stop_access.csv", index=False)

    reachable = out["best_min"].notna() & (out["best_min"] < MAX_JOURNEY_MIN)
    print()
    print(f"stops with any hospital journey : {int(reachable.sum()):,} "
          f"({reachable.mean():.1%})")
    print(f"median journey from a stop      : {out.loc[reachable, 'best_min'].median():.0f} min")
    print(f"stops needing a change          : {int(out['needs_change'].sum()):,}")


if __name__ == "__main__":
    main()
