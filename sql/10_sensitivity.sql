-- The same population figure under each assumption, side by side.
-- If the headline moves a lot here, the headline is not worth much.

SELECT 'headline (500 m walk, all routes)'  AS assumption,
       SUM(CASE WHEN median_min          >= 45 THEN population END) AS people_over_45
FROM wards
UNION ALL
SELECT 'walk up to 800 m to a stop',
       SUM(CASE WHEN median_800m         >= 45 THEN population END) FROM wards
UNION ALL
SELECT 'only routes every 30 min or better',
       SUM(CASE WHEN median_frequent     >= 45 THEN population END) FROM wards
UNION ALL
SELECT 'excluding single-specialty hospitals',
       SUM(CASE WHEN median_general      >= 45 THEN population END) FROM wards
UNION ALL
SELECT 'no changing buses',
       SUM(CASE WHEN median_direct_only  >= 45 THEN population END) FROM wards;
