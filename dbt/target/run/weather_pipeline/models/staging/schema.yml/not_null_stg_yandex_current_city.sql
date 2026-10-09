
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select city
from `weather_staging`.`stg_yandex_current`
where city is null



  
  
    ) dbt_internal_test