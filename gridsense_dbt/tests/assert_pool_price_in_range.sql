select *
from {{ ref('stg_pool_price') }}
where pool_price < 0
   or pool_price > 999.99