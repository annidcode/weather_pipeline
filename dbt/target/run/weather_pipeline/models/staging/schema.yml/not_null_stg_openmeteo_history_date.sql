
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select date
from `weather_staging`.`stg_openmeteo_history`
where date is null



  
  
    ) dbt_internal_test