-- One row per day: how good was the forecast vs the real price?

with forecasts as (
    select forecast_for_utc, forecast_date, predicted_price
    from {{ source('aeso', 'forecasts') }}
    where model_name = 'lightgbm_v1'
),

prices as (
    -- work out "same as yesterday" BEFORE joining (like SQL Question 7)
    select
        hour_start_utc,
        pool_price,
        lag(pool_price, 24) over (order by hour_start_utc) as yesterday_price
    from {{ ref('stg_pool_price') }}
)

select
    f.forecast_date,
    count(*)                                              as hours_compared,
    round(avg(p.pool_price), 2)                           as avg_real_price,
    round(avg(f.predicted_price), 2)                      as avg_predicted_price,
    round(avg(abs(p.pool_price - f.predicted_price)), 2)  as model_mae,
    round(avg(abs(p.pool_price - p.yesterday_price)), 2)  as yesterday_mae
from forecasts f
join prices p
    on p.hour_start_utc = f.forecast_for_utc
where p.pool_price is not null          -- only hours that have a real price
group by f.forecast_date
order by f.forecast_date