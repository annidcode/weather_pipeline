

SELECT
    city,
    latitude,
    longitude,
    population,
    toDateTime(timestamp) AS observed_at,
    temp,
    feels_like,
    condition,
    humidity,
    pressure_mm,
    wind_speed,
    wind_dir,
    wind_gust,
    uv_index,
    prec_strength,
    prec_type,
    cloudness,
    magnetic_field
FROM `default`.`raw_weather_current`