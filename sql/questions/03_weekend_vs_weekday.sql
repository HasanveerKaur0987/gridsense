-- Q3a: Weekend vs weekday, all years together
select
    case
        when day_of_week in (6, 7) then 'weekend'
        else 'weekday'
    end                         as day_type,
    round(avg(pool_price), 2)   as avg_price,
    count(pool_price)           as hours_counted
from analytics.stg_pool_price
group by day_type
order by avg_price desc;




-- Q3b: Weekend vs weekday, per year
select
    year,
    case
        when day_of_week in (6, 7) then 'weekend'
        else 'weekday'
    end                         as day_type,
    round(avg(pool_price), 2)   as avg_price
from analytics.stg_pool_price
group by year, day_type
order by year, day_type;

-- FINDINGS:
-- All years: weekday avg $76.55, weekend avg $54.02 → weekends ~29% cheaper
-- Per year (weekend cheaper by): 2023 33%, 2024 14%, 2025 34%, 2026 43%
-- Weekend is cheaper EVERY year → strong pattern (likely lower business/industry demand)
-- 2024 gap is smallest → worth checking (Jan 2024 cold snap?)
-- Compared % not $ because price levels changed a lot between years