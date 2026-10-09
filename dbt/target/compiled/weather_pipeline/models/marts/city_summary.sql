

SELECT
    city,
    latitude,
    longitude,
    COUNT(*) AS days_count,
    ROUND(AVG(temp_mean), 2) AS avg_temp,
    ROUND(MIN(temp_min), 2) AS min_temp,
    ROUND(MAX(temp_max), 2) AS max_temp,
    ROUND(SUM(precipitation), 2) AS total_precipitation,
    ROUND(AVG(wind_speed_max), 2) AS avg_wind,
    ROUND(MAX(wind_gusts_max), 2) AS max_gust
FROM `weather_staging`.`stg_openmeteo_history`
GROUP BY city, latitude, longitude
ORDER BY avg_temp DESC