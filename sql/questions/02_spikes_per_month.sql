-- Q2: How many price spikes ($100+) happen each month?
select
    year,
    month,
    count(*) filter (where pool_price >= 100)  as spike_hours,
    count(pool_price)                           as total_hours,
    round(100.0 * count(*) filter (where pool_price >= 100)
          / count(pool_price), 1)               as spike_pct,
    round(avg(pool_price), 2)                   as avg_price
from analytics.stg_pool_price
group by year, month
order by year, month;

-- FINDINGS (spike = price >= $100):
-- 2023: 2,446 spike hours (27.9% of hours)
-- 2024:   990 (11.3%)
-- 2025:   452 (5.2%)
-- 2026:   267 so far (3.8%)
-- Spikes dropped ~7x from 2023 to 2026; monthly avg price fell from $100–187 (2023) to $17–46 (2026)
-- Worst month: Mar 2023 (40.1%). Calmest: Dec 2024 (0.9%). Jan 2024 jump (29%) = likely cold snap.
-- Big change happened in early-mid 2024 → matters for the forecast train/test split