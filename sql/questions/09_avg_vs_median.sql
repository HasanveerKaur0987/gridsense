-- Q9: Average vs median price per year
select
    year,
    round(avg(pool_price), 2)                                               as avg_price,
    round((percentile_cont(0.5) within group (order by pool_price))::numeric, 2) as median_price,
    round((percentile_cont(0.9) within group (order by pool_price))::numeric, 2) as p90_price,
    max(pool_price)                                                         as max_price
from analytics.stg_pool_price
where pool_price is not null
group by year
order by year;


-- FINDINGS:
--        avg      median   p90      max
-- 2023  $133.63   $57.20  $367.74  $999.99
-- 2024   $62.78   $30.56  $112.22  $999.99
-- 2025   $43.68   $22.91   $63.95  $999.99
-- 2026   $33.44   $18.72   $50.64  $999.99
-- Average ≈ 2x median every year → spikes pull the avg up; most hours are below average
-- 2023 → 2026: median -67%, avg -75%, p90 -86% → expensive hours calmed down the most
-- Max still $999.99 every year → spikes rarer, not gone
-- Dashboard: show median as "typical price", avg next to it
-- Skill: percentile_cont(0.5 / 0.9) WITHIN GROUP (ORDER BY ...)