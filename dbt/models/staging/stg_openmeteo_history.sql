{{ config(materialized='view') }}

SELECT
    city,
    latitude,
    longitude,
    date,
    temp_max,
    temp_min,
    temp_mean,
    precipitation,
    wind_speed_max,
    wind_gusts_max
FROM {{ source('raw', 'raw_weather_history') }}
