

  create or replace view `weather_staging`.`stg_openmeteo_history` 
  
    
  
  
    
    
  as (
    

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
FROM `default`.`raw_weather_history`
    
  )
      
      
                    -- end_of_sql
                    
                    