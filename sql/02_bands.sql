-- Wards and people in each journey-time band.
-- The population column matters more than the ward column: wards are not
-- equal in size, and the badly served ones are large and thinly mapped.

SELECT
    band,
    COUNT(*)                                        AS wards,
    SUM(population)                                 AS people,
    ROUND(100.0 * SUM(population) / (SELECT SUM(population) FROM wards), 1) AS pct_of_city,
    ROUND(MIN(median_min), 1)                       AS fastest_ward,
    ROUND(MAX(median_min), 1)                       AS slowest_ward
FROM wards
GROUP BY band
ORDER BY fastest_ward;
