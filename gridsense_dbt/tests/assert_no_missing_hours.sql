with bounds as (
    -- the first and last hour we have
    select
        min(hour_start_utc) as first_hour,
        max(hour_start_utc) as last_hour
    from {{ ref('stg_pool_price') }}
),

expected as (
    -- every hour that SHOULD exist
    select generate_series(first_hour, last_hour, interval '1 hour') as hour_start_utc   -- ← '1 hour'
    from bounds
)

-- hours on the list that are NOT in our data
select e.hour_start_utc
from expected e
left join {{ ref('stg_pool_price') }} s          -- ← left
    on e.hour_start_utc = s.hour_start_utc
where s.hour_start_utc is null                   -- ← null