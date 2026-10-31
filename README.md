# GridSense ⚡

**A live data platform for the Alberta electricity market.**
Every hour it loads new pool prices from AESO, cleans and tests them with dbt, and shows the results on a public dashboard.

🔗 **Live dashboard:** https://gridsense-alberta.streamlit.app

---

## What it does

```
AESO public API
     ↓  Python + GitHub Actions (every hour)
PostgreSQL on Neon: raw_pool_price        ← raw data, never changed
     ↓  dbt (runs right after each load)
analytics.stg_pool_price (view)           ← clean hourly data
analytics.daily_prices (table)            ← one row per day
     ↓  6 dbt data tests
Streamlit dashboard (public link)
```

- **33,000+ hours** of prices, from Jan 1, 2023 to now
- **No missing hours and no duplicates**, checked by dbt tests on every run
- **10 SQL analysis questions** answered with CTEs and window functions (`sql/questions/`)

## Key findings

1. **Evenings are the most expensive time.** 7–8 PM averages **$137/MWh**, while 3–4 AM averages **$35/MWh**, about 4 times less. Demand is high in the evening, and solar stops after sunset.
2. **Price spikes almost disappeared.** In 2023, **27.9%** of hours were $100/MWh or more. In 2026 (so far), it's **3.8%**.
3. **Weekends are cheaper every year**, by 14% to 43% depending on the year.
4. **The January 2024 cold snap** was the most expensive week in the data: Jan 11–17, 2024 averaged **$420/MWh per day**. Jan 14, 2024 was the most expensive single day ($707/MWh).
5. **The average price misleads.** It is about **2 times the median** every year, because a few spike hours pull it up. In 2026, a typical hour (median) costs **$18.72**, but the average is $33.44.

*Numbers are as of Oct 23, 2026. The live dashboard always shows the latest data.*

## Hard problems I solved

| Problem | What I did | Why |
| --- | --- | --- |
| **Daylight saving time** | Stored every hour in **UTC** as the primary key; showed Alberta time only on screen | In Alberta time, 1:00 AM happens twice in November and 2:00 AM never happens in March. UTC never repeats or skips |
| **AESO dates are Alberta dates** | The loader asks for Alberta "yesterday + today", not UTC dates | GitHub's servers run on UTC, so "today" would be wrong for 6–7 hours a day |
| **Prices arrive late** | Unfinished hours are saved as NULL and filled in on a later run (counted as "updated") | AESO posts final prices with a delay |
| **GitHub Actions skips scheduled runs** | Every run re-loads the last 2 days, safe to re-run (upsert, no duplicates) | Only about 1 in 4 hourly runs actually started in the first days, but **no data was lost**, and the missing-hours test proves it |
| **Keeping the database safe** | The public dashboard uses a **read-only** database user | Even if that password leaked, nobody could change or delete data |

## Data quality tests (dbt)

- `hour_start_utc` is **unique** and **not null**
- `price_date` in `daily_prices` is **unique** and **not null**
- **No missing hours:** every UTC hour from the first to the last is present
- **Prices are in range:** between $0 and $999.99 (Alberta's price cap)

If any test fails, the GitHub Actions run turns red.

## Tech stack

| Part | Tool |
| --- | --- |
| Data source | AESO public API (pool price) |
| Loading | Python, psycopg, GitHub Actions (hourly) |
| Database | PostgreSQL 18 on Neon |
| Cleaning + tests | dbt (dbt-core 1.11, dbt-postgres) |
| Analysis | SQL (CTEs, `RANK`, `LAG`, rolling averages, `percentile_cont`) |
| Dashboard | Streamlit (Streamlit Community Cloud) |

## Project layout

```
gridsense/
├── .github/workflows/ingest.yml   # hourly: load prices, then dbt build
├── scripts/ingest_pool_price.py   # the loader (hourly + backfill modes)
├── sql/
│   ├── 001_create_tables.sql      # raw_pool_price + ingest_runs
│   └── questions/                 # 10 SQL analysis questions + findings
├── gridsense_dbt/                 # dbt models and tests
│   ├── models/staging/            # stg_pool_price
│   ├── models/marts/              # daily_prices
│   └── tests/                     # missing hours, price range
└── dashboard/app.py               # Streamlit dashboard
```

## Run it yourself

1. Get a free API key at [developer-apim.aeso.ca](https://developer-apim.aeso.ca) and a free PostgreSQL database (for example, Neon).
2. Make a `.env` file with `AESO_API_KEY`, `DATABASE_URL`, `PGHOST`, `PGUSER`, `PGPASSWORD` and `PGDATABASE`.
3. Install packages and create the tables:
   ```bash
   pip install -r requirements.txt
   python scripts/create_tables.py
   ```
4. Load data, then build and test:
   ```bash
   python scripts/ingest_pool_price.py --start 2023-01-01
   cd gridsense_dbt && dbt build --profiles-dir .
   ```
5. Start the dashboard:
   ```bash
   streamlit run dashboard/app.py
   ```

## Coming next

- Next-day price forecast, measured against two simple baselines ("same as yesterday" and "same as last week")
- Daily tracking of forecast error on the dashboard