select
    price_date,
    count(*)                    as hours_in_day,
    count(pool_price)           as final_hours,
    round(avg(pool_price), 2)   as avg_price,
    min(pool_price)             as min_price,
    max(pool_price)             as max_price,
    count(pool_price) = count(*) as is_complete
from {{ ref('stg_pool_price') }}
group by price_date
order by price_date