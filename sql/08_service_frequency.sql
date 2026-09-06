-- The frequency profile of the feed. This is the number that surprised me
-- most: the median BMTC pattern in the timetable runs a couple of times a day.

SELECT
    CASE
        WHEN headway_min <= 15  THEN 'every 15 min or better'
        WHEN headway_min <= 30  THEN '15 to 30 min'
        WHEN headway_min <= 60  THEN '30 to 60 min'
        WHEN headway_min <= 240 THEN '1 to 4 hours'
        ELSE 'less than four times a day'
    END                                  AS frequency,
    COUNT(*)                             AS patterns,
    SUM(n_trips)                         AS daily_trips,
    ROUND(AVG(n_stops), 1)               AS mean_stops_per_pattern
FROM patterns
GROUP BY frequency
ORDER BY daily_trips DESC;
