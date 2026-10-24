-- Q5: How did each month's price change from the month before?

-- Step 1: average price per month
with monthly as (
    select
        date_trunc('month', price_date)::date  as month_start,
        round(avg(pool_price), 2)              as avg_price
    from analytics.stg_pool_price
    group by month_start
),

-- Step 2: put last month's price next to this month
with_prev as (
    select
        month_start,
        avg_price,
        lag(avg_price) over (order by month_start)  as prev_price
    from monthly
)

-- Step 3: work out the change
select
    month_start,
    avg_price,
    prev_price,
    avg_price - prev_price                                  as change,
    round(100.0 * (avg_price - prev_price) / prev_price, 1) as change_pct
from with_prev
order by month_start;


-- FINDINGS:
-- Biggest jump: Jan 2024, +193.5% ($52 → $153) → cold snap again (also in Q2 and Q4)
-- 2nd: Jul 2024, +178.2% ($32 → $89)
-- Biggest drop: Dec 2024, -63.0% ($71 → $26); 2nd: Aug 2024, -61.3%
-- Careful: with low 2026 prices, small $ changes look huge in % (Jul 2026: +80% = only +$13.90)
-- Monthly prices swing ±40%+ often → hard to forecast
-- Oct 2026 is a partial month
-- Skills: 2 CTEs in a row, LAG() OVER (ORDER BY), date_trunc