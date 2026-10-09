
    
    

select
    city as unique_field,
    count(*) as n_records

from `weather_staging`.`stg_yandex_current`
where city is not null
group by city
having count(*) > 1


