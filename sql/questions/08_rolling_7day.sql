-- Q8a: Daily price vs 7-day rolling average (last 14 days)
with rolling as (
    select
        price_date,
        avg_price,
        round(avg(avg_price) over (
            order by price_date
            rows between 6 preceding and current row
        ), 2)                                    as rolling_7d
    from analytics.daily_prices
    where is_complete
)
select *
from rolling
order by price_date desc
limit 14;

-- Q8b: Highest 7-day rolling averages (worst weeks)
with rolling as (
    select
        price_date,
        round(avg(avg_price) over (
            order by price_date
            rows between 6 preceding and current row
        ), 2)                                    as rolling_7d
    from analytics.daily_prices
    where is_complete
)
select *
from rolling
order by rolling_7d desc
limit 5;



-- FINDINGS:
-- Worst week ever: Jan 11–17, 2024, 7-day avg $420.04/day (~14x a normal 2026 day)
-- → Jan 2024 cold snap, now confirmed by Q2, Q4, Q5, Q8
-- 4 of top 5 weeks overlap (neighbouring windows share 6 of 7 days)
-- 5th worst: Jun 2–8, 2023 ($363.53), includes Jun 7, 2023 (top 2023 day from Q4)
-- Last 14 days: daily $6.82–$123.86, rolling $26.70–$73.11 → much smoother
-- A spike stays in the 7-day avg for exactly 7 days, then drops out (Oct 13 spike → Oct 20 drop)
-- Skill: AVG() OVER (ORDER BY ... ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)