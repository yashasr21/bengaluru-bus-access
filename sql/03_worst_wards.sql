-- The twenty wards with the longest typical journey.
-- straight_line_km is carried along so the reader can see at once whether the
-- ward is simply far away or badly connected.

SELECT
    ward_label,
    ROUND(median_min, 1)        AS typical_minutes,
    ROUND(best_min, 1)          AS best_corner,
    ROUND(worst_min, 1)         AS worst_corner,
    population,
    ROUND(straight_line_km, 1)  AS km_to_nearest_hospital,
    ROUND(share_reachable, 2)   AS share_of_ward_with_any_journey
FROM wards
ORDER BY median_min DESC
LIMIT 20;
