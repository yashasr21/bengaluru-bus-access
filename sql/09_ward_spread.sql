-- Where the story is inside a ward rather than between wards.
-- A large gap between the best and worst corner means the ward average hides
-- a real divide; those are the places worth visiting before writing anything.

SELECT
    ward_label,
    ROUND(best_min, 1)              AS best_corner,
    ROUND(median_min, 1)            AS typical,
    ROUND(worst_min, 1)             AS worst_corner,
    ROUND(worst_min - best_min, 1)  AS spread,
    sample_points,
    population
FROM wards
WHERE sample_points >= 20
ORDER BY spread DESC
LIMIT 12;
