

  create or replace view `weather_staging`.`stg_yandex_forecast` 
  
    
  
  
    
    
  as (
    

SELECT
    city,
    region,
    latitude,
    longitude,
    date,
    temp_max,
    temp_min,
    temp_avg,
    precipitation,
    wind_speed,
    wind_gust,
    condition,
    uv_index,
    humidity
FROM `default`.`raw_weather_forecast`
    
  )
      
      
                    -- end_of_sql
                    
                    