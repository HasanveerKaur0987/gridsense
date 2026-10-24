-- Q1: Which hour of the day has the highest average price?
select
    hour_ending,
    round(avg(pool_price), 2) as avg_price,
    max(pool_price)           as max_price,
    count(pool_price)         as hours_counted
from analytics.stg_pool_price
group by hour_ending
order by avg_price desc;

-- FINDINGS (Jan 2023 – Oct 2026):
-- Most expensive: HE20 (7–8 PM), avg $137.14
-- Cheapest: HE4 (3–4 AM), avg $35.10 → evening is about 4x the price of night
-- Why: evening demand is high (home, cooking, heating) and solar stops after sunset
-- Small midday dip (HE11–13) when solar is strongest
-- DST check: HE2 has 1,395 hours (3 fall-back days), HE3 has 1,388 (4 spring-forward days)

