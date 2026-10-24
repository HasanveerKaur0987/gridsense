-- Q6: How accurate is AESO's own price forecast? (per year)
select
    year,
    count(*)                                                    as hours,
    round(avg(pool_price), 2)                                   as avg_price,
    round(avg(abs(pool_price - forecast_pool_price)), 2)        as mae,
    round(100.0 * avg(abs(pool_price - forecast_pool_price))
          / avg(pool_price), 1)                                 as mae_pct,
    round(avg(forecast_pool_price - pool_price), 2)             as bias
from analytics.stg_pool_price
where pool_price is not null              -- only hours with a real price
  and forecast_pool_price is not null     -- and a forecast
group by year
order by year;

-- FINDINGS:
-- AESO MAE: 2023 $42.11 → 2026 $11.27 (looks better in $)
-- But MAE %: 31.5%, 28.6%, 36.8%, 33.7% → about the same every year
-- → AESO didn't really improve; prices just got lower (compare % when price levels change)
-- Bias positive every year (+$2.76 to +$7.59) → AESO always guesses too high
-- NOTE: stored forecast = AESO's LAST update before the hour (short-term),
--       so it's a tough reference, not a fair benchmark for a next-day model.
--       Fair benchmarks for Week 4 = "same as yesterday" and "same as last week".