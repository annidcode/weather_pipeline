{{ config(materialized='table') }}

SELECT
    city,
    date,
    temp_max,
    temp_min,
    temp_mean,
    precipitation,
    wind_speed_max,
    wind_gusts_max,
    -- Скользящее среднее за 7 дней
    AVG(temp_mean) OVER (
        PARTITION BY city
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS temp_mean_7d,
    -- Отклонение от среднего за 30 дней
    temp_mean - AVG(temp_mean) OVER (
        PARTITION BY city
        ORDER BY date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS temp_anomaly
FROM {{ ref('stg_openmeteo_history') }}
