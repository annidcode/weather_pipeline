
  
    
    
    
        


        
  

  insert into `weather_marts`.`weather_anomalies__dbt_backup`
        ("city", "date", "temp_mean", "avg_temp", "std_temp", "z_score", "flag")

WITH stats AS (
    SELECT
        city,
        AVG(temp_mean) AS avg_temp,
        stddevPop(temp_mean) AS std_temp
    FROM `weather_staging`.`stg_openmeteo_history`
    GROUP BY city
)

SELECT
    w.city,
    w.date,
    w.temp_mean,
    s.avg_temp,
    s.std_temp,
    ROUND((w.temp_mean - s.avg_temp) / NULLIF(s.std_temp, 0), 2) AS z_score,
    CASE
        WHEN ABS((w.temp_mean - s.avg_temp) / NULLIF(s.std_temp, 0)) > 2 THEN 'anomaly'
        WHEN ABS((w.temp_mean - s.avg_temp) / NULLIF(s.std_temp, 0)) > 1.5 THEN 'warning'
        ELSE 'normal'
    END AS flag
FROM `weather_staging`.`stg_openmeteo_history` w
JOIN stats s ON w.city = s.city
WHERE ABS((w.temp_mean - s.avg_temp) / NULLIF(s.std_temp, 0)) > 1.5
ORDER BY z_score DESC
  