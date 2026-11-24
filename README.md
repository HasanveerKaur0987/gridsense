# GridSense ⚡

[![Tests](https://github.com/HasanveerKaur0987/gridsense/actions/workflows/ci.yml/badge.svg)](https://github.com/HasanveerKaur0987/gridsense/actions/workflows/ci.yml)

**A live data platform and price forecast for the Alberta electricity market.**
Every hour it loads new prices from AESO, cleans and tests them with dbt, and every day it forecasts tomorrow's 24 hourly prices with a LightGBM model.

🔗 **Live dashboard:** https://gridsense-alberta.streamlit.app

---

## How it works

```
AESO public API
     ↓  Python loader, runs every hour on GitHub Actions
PostgreSQL (Neon): raw prices + a log of every load
     ↓  dbt: clean models + 8 data quality tests
analytics tables (hourly, daily, forecast accuracy)
     ↓  LightGBM: forecast the next day's 24 hourly prices
Streamlit dashboard (public, read-only database user)
```

- **34,000+ hours** of prices, from Jan 2023 to now, with **no missing hours** (checked by a dbt test on every run)
- Fully automatic: loading, testing and forecasting all run with no manual steps

## Forecast results

The model predicts each hour of the next day, using only data known by midnight.

**Backtest:** trained on Jan 2023 to Jun 2025, tested on 11,682 unseen hours (Jul 2025 to Oct 2026)

| Forecast | Average miss (MAE, $/MWh) |
| --- | --- |
| **LightGBM (my model)** | **$30.34** |
| Same as yesterday | $42.05 |
| Same as last week | $46.16 |

**27.8% better than "same as yesterday"**, the usual baseline for price forecasts.

**Live, since Oct 30, 2026:** the model's average miss is **$18.50** vs **$30.73** for "same as yesterday" (**40% better**), and it beat the baseline on **20 of 25 days** (as of Nov 24, 2026).

**Where it struggles:** on normal hours (95% of the time) it is about **48% better** than the baseline. It does not predict sudden price spikes, and those few hours cause about half of all its error. Predicting them would need outage, weather and wind data.

## Key findings

1. **Evenings cost about 4 times more than nights:** 7–8 PM averages $137/MWh vs $35/MWh at 3–4 AM.
2. **Price spikes almost disappeared:** 27.9% of hours were $100/MWh or more in 2023, only 3.8% in 2026.
3. **The January 2024 cold snap** was the most expensive week in the data. Jan 14, 2024 averaged $707/MWh.
4. **The average price misleads:** it is about 2 times the median, because a few spike hours pull it up.

All 10 analysis questions (CTEs, window functions) are in [`sql/questions/`](sql/questions/).

## Hard problems I solved

| Problem | Solution |
| --- | --- |
| **Clock changes** | Every hour is stored in **UTC**, so no hour repeats or goes missing. When Alberta stopped changing clocks in Nov 2026, the pipeline needed **no changes** |
| **No peeking at the future** | Time-based train/test split, and each forecast only uses prices up to midnight before the forecast day |
| **GitHub skips scheduled runs** | Every run reloads the last 2 days with an upsert (no duplicates), so a skipped run loses no data. The missing-hours test proves it |
| **Prices arrive late** | Unfinished hours are saved as empty and filled in on a later run |
| **Keeping data safe** | The public dashboard uses a **read-only** database user. Secrets live in `.env`, GitHub Secrets and Streamlit Secrets, never in code |

## Testing

- **Data tests (dbt):** unique, not-null, no missing hours, prices in range. They run after every hourly load, and a failure turns the run red.
- **Code tests (pytest + GitHub Actions):** run on every push. They check the forecast features with small fake data, so they need no database or secrets.

## Tech stack

**Python** (pandas, psycopg, LightGBM) · **SQL** · **PostgreSQL** (Neon) · **dbt** · **GitHub Actions** · **Streamlit** · **Docker** · **pytest**

## Run it yourself

1. Get a free AESO API key at [developer-apim.aeso.ca](https://developer-apim.aeso.ca) and a free PostgreSQL database (for example, Neon).
2. Make a `.env` file with `AESO_API_KEY`, `DATABASE_URL`, `PGHOST`, `PGUSER`, `PGPASSWORD` and `PGDATABASE`.
3. Install, create the tables, load data and build:
   ```bash
   pip install -r requirements.txt
   python scripts/create_tables.py          # also run sql/002_create_forecasts.sql
   python scripts/ingest_pool_price.py --start 2023-01-01
   cd gridsense_dbt && dbt build --profiles-dir . && cd ..
   python forecast/predict_today.py
   ```
4. Start the dashboard, with Python or Docker:
   ```bash
   streamlit run dashboard/app.py
   ```
   ```bash
   docker build -t gridsense-dashboard .
   set -a; source .env; set +a
   docker run --rm -p 8501:8501 -e DATABASE_URL gridsense-dashboard
   ```
   Then open http://localhost:8501.

## Project layout

```
gridsense/
├── scripts/            # create tables, hourly loader (with backfill mode)
├── sql/                # table definitions + 10 analysis questions
├── gridsense_dbt/      # dbt models and data tests
├── forecast/           # features, training, daily forecast
├── dashboard/          # Streamlit app
├── tests/              # pytest tests
├── Dockerfile          # dashboard container
└── .github/workflows/  # hourly pipeline + CI tests
```
