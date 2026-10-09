
  
    
    
    
        


        
  

  insert into `weather_marts`.`daily_weather`
        ("city", "date", "temp_max", "temp_min", "temp_mean", "precipitation", "wind_speed_max", "wind_gusts_max", "temp_mean_7d", "temp_anomaly")

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
FROM `weather_staging`.`stg_openmeteo_history`
  