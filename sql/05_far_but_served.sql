-- The opposite case. Wards a long way from any hospital that still do
-- reasonably well, usually because one good route runs straight through.

SELECT
    ward_label,
    ROUND(median_min, 1)        AS typical_minutes,
    ROUND(straight_line_km, 1)  AS km_to_nearest_hospital,
    ROUND(penalty_ratio, 2)     AS bus_vs_crow,
    population
FROM wards
WHERE straight_line_km > 4
ORDER BY median_min ASC
LIMIT 12;
