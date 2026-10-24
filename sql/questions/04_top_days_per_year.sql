-- Q4: Top 3 most expensive days in each year

-- Step 1: give every day a rank inside its year
with ranked_days as (
    select
        extract(year from price_date)  as year,
        price_date,
        avg_price,
        max_price,
        rank() over (
            partition by extract(year from price_date)
            order by avg_price desc
        )                              as day_rank
    from analytics.daily_prices
    where is_complete              -- skip today (not finished yet)
)

-- Step 2: keep only the top 3 of each year
select year, day_rank, price_date, avg_price, max_price
from ranked_days
where day_rank <= 3
order by year, day_rank;


-- FINDINGS:
-- Most expensive day in all data: 2024-01-14, avg $707.12 (~20x a normal 2026 day)
-- 2024 top 3 = Jan 12, 13, 14 in a row → confirms the Jan 2024 cold snap seen in Q2
-- 2023 top days were in late spring/summer (May 24, Jun 7, Aug 28) → not only winter
-- Almost every top day hit the $999.99 price cap
-- Top days got milder: 2023–24 avg $530–707 vs 2025–26 avg $270–410
-- Used daily_prices (dbt table) + CTE + RANK() OVER (PARTITION BY year)