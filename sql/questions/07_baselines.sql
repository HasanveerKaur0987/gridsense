-- Q7: How good are simple baselines vs AESO's forecast? (MAE per year)

-- Step 1: for every hour, find the price 24h ago and 168h ago
with with_baselines as (
    select
        year,
        pool_price,
        forecast_pool_price,
        lag(pool_price, 24)  over (order by hour_start_utc)  as yesterday_price,
        lag(pool_price, 168) over (order by hour_start_utc)  as last_week_price
    from analytics.stg_pool_price
)

-- Step 2: grade each forecast with MAE
select
    year,
    count(*)                                               as hours,
    round(avg(abs(pool_price - yesterday_price)), 2)       as mae_yesterday,
    round(avg(abs(pool_price - last_week_price)), 2)       as mae_last_week,
    round(avg(abs(pool_price - forecast_pool_price)), 2)   as mae_aeso
from with_baselines
where pool_price is not null
  and yesterday_price is not null
  and last_week_price is not null
  and forecast_pool_price is not null
group by year
order by year;

-- FINDINGS (MAE, smaller = better):
--        yesterday  last_week  AESO
-- 2023    $113.53    $134.80   $42.43
-- 2024     $53.83     $68.08   $17.97
-- 2025     $45.63     $49.52   $16.07
-- 2026     $35.07     $39.66   $11.27
-- "Same as yesterday" beats "same as last week" every year
-- AESO ~3x better, but its forecast is short-term (made close to the hour) → not a fair race
-- 2026 yesterday MAE ($35.07) > 2026 avg price ($33.44) → hourly prices very noisy (spikes)
-- WEEK 4 TARGET: model must beat "same as yesterday" on the test period
-- 2023 hours = 8,592 (first 168 hours have no "last week" value)