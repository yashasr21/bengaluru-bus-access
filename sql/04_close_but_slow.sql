-- Wards that are physically near a hospital but slow to reach one by bus.
-- penalty_ratio compares the bus journey with the time it would take to walk
-- the straight-line distance. Above 1 means the bus is slower than the crow,
-- which is the signature of a missing route rather than a missing hospital.

SELECT
    ward_label,
    ROUND(median_min, 1)        AS typical_minutes,
    ROUND(straight_line_km, 1)  AS km_to_nearest_hospital,
    ROUND(penalty_ratio, 2)     AS bus_vs_crow,
    population
FROM wards
WHERE straight_line_km < 4
ORDER BY penalty_ratio DESC
LIMIT 12;
