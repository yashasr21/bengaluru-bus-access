-- How the city as a whole comes out.
-- One row. This is the number I would open an interview answer with.

SELECT
    COUNT(*)                                          AS wards,
    SUM(population)                                   AS people,
    ROUND(AVG(median_min), 1)                         AS mean_ward_minutes,
    SUM(CASE WHEN median_min <  30 THEN population END) AS people_under_30,
    SUM(CASE WHEN median_min >= 45 THEN population END) AS people_over_45,
    SUM(CASE WHEN median_min >= 60 THEN population END) AS people_over_60,
    ROUND(100.0 * SUM(CASE WHEN median_min >= 45 THEN population END)
          / SUM(population), 1)                       AS pct_over_45
FROM wards;
