-- How much of the network depends on changing buses.
-- direct_min is the journey with one bus; best_min allows one change.

SELECT
    CASE
        WHEN direct_min IS NOT NULL                      THEN 'reached with one bus'
        WHEN direct_min IS NULL AND best_min IS NOT NULL THEN 'needs a change'
        ELSE 'no bus journey at all'
    END                                          AS situation,
    COUNT(*)                                     AS stops,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM stops), 1) AS pct_of_stops,
    ROUND(AVG(best_min), 1)                      AS mean_minutes
FROM stops
GROUP BY situation
ORDER BY stops DESC;
