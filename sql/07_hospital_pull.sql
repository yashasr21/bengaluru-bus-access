-- Which hospitals the network actually delivers people to.
-- Each stop is assigned to its nearest hospital; the count is a rough measure
-- of how much of the city leans on each site.

SELECT
    s.nearest_hospital,
    h.facility_type,
    COUNT(*)                          AS stops_nearest_to_it,
    ROUND(AVG(s.metres_to_hospital))  AS mean_metres
FROM stops s
JOIN hospitals h ON h.name = s.nearest_hospital
GROUP BY s.nearest_hospital, h.facility_type
ORDER BY stops_nearest_to_it DESC
LIMIT 15;
