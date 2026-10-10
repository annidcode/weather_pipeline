

SELECT
    region,
    COUNT(*) AS rows_count,
    COUNT(DISTINCT city) AS cities_count,
    ROUND(AVG(temp_mean), 2) AS avg_temp,
    ROUND(MIN(temp_min), 2) AS min_temp,
    ROUND(MAX(temp_max), 2) AS max_temp,
    ROUND(SUM(precipitation), 2) AS total_precipitation,
    ROUND(MAX(wind_gusts_max), 2) AS max_gust
FROM `weather_staging`.`stg_openmeteo_history`
GROUP BY region
ORDER BY avg_temp DESC