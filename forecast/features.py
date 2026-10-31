"""Week 4, step 1: load hourly prices and build features for the forecast.

Run from the gridsense folder:
    python forecast/features.py

The forecast is made at MIDNIGHT (Alberta time) for each hour of the next day.
So every feature may only use prices that are known by that midnight.
"""
import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

FEATURES = [
    "hour_ending",   # 1-24: evenings are expensive (Q1)
    "day_of_week",   # 1-7: weekends are cheaper (Q3)
    "month",         # 1-12: seasons
    "is_weekend",    # 0 or 1
    "lag_24",        # price at the same hour yesterday ("same as yesterday" baseline)
    "lag_48",        # price at the same hour 2 days ago
    "lag_168",       # price at the same hour last week ("same as last week" baseline)
    "prev_day_avg",  # yesterday's average price
    "prev_day_max",  # yesterday's highest price (was there a spike?)
]


# ---------- 1. Load data from Neon ----------
def load_data():
    sql = """
        select hour_start_utc,
               price_date,
               hour_ending::int  as hour_ending,
               day_of_week::int  as day_of_week,
               month::int        as month,
               year::int         as year,
               pool_price
        from analytics.stg_pool_price
        order by hour_start_utc
    """
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(sql)
        columns = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)

    df["pool_price"] = pd.to_numeric(df["pool_price"])  # Decimal -> float, empty -> NaN
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


# ---------- 2. Build features ----------
def add_features(df, drop_missing=True):
    df = df.copy()

    df["is_weekend"] = df["day_of_week"].isin([6, 7]).astype(int)

    # Lags: our data has exactly 1 row per hour with no gaps (dbt test proves it),
    # so "24 rows back" = 24 hours ago.
    df["lag_24"] = df["pool_price"].shift(24)
    df["lag_48"] = df["pool_price"].shift(48)
    df["lag_168"] = df["pool_price"].shift(168)

    # Yesterday's average and max, joined onto every hour of today
    daily = df.groupby("price_date")["pool_price"].agg(["mean", "max"])
    daily.index = daily.index + pd.Timedelta(days=1)  # move each day forward by 1
    df["prev_day_avg"] = df["price_date"].map(daily["mean"])
    df["prev_day_max"] = df["price_date"].map(daily["max"])

    # Keep only rows where we know the real price and all features
    # (predict_today.py turns this off, because today's prices are not known yet)
    if drop_missing:
        df = df.dropna(subset=["pool_price"] + FEATURES)
    return df


# ---------- 3. Check it (only when run directly) ----------
if __name__ == "__main__":
    data = add_features(load_data())

    print(f"Rows ready for the model: {len(data):,}")
    print(f"From {data['price_date'].min():%Y-%m-%d} to {data['price_date'].max():%Y-%m-%d}")
    print()
    print(data[["hour_start_utc", "pool_price"] + FEATURES].tail(3).to_string(index=False))

    # Sanity check: should be close to SQL Question 7 ($35.07 for 2026 on Oct 23;
    # a little different now because there is more data)
    y2026 = data[data["year"] == 2026]
    mae = (y2026["pool_price"] - y2026["lag_24"]).abs().mean()
    print(f"\nCheck: 'same as yesterday' MAE in 2026 = ${mae:.2f} (SQL Q7 on Oct 23: $35.07)")