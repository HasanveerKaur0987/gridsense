"""Week 4, step 3B: forecast every hour of TODAY (Alberta) and save it to Neon.

Run from the gridsense folder:
    python forecast/predict_today.py

Safe to run many times a day (GitHub Actions runs it every hour):
  - if today's forecast is already saved      -> does nothing
  - if yesterday's prices are not all in yet  -> waits for a later run
  - otherwise                                 -> trains, forecasts, saves
The model only uses prices up to the end of YESTERDAY, so the forecast is
exactly what we could have made at midnight (no peeking at today).
"""
import os
from datetime import datetime, timedelta, timezone

import lightgbm as lgb
import pandas as pd
import psycopg
from dotenv import load_dotenv

from features import FEATURES, add_features, load_data

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_NAME = "lightgbm_v1"

# Since Nov 1, 2026, Alberta Time (ABT) is UTC-6 all year (no more clock changes).
ABT = timezone(timedelta(hours=-6), "ABT")


# ---------- 1. The 24 hours we want to forecast ----------
def future_hours(target_date):
    start_utc = pd.Timestamp(target_date) + pd.Timedelta(hours=6)  # 00:00 ABT = 06:00 UTC
    hours_utc = pd.date_range(start_utc, periods=24, freq="h", tz="UTC")
    local = hours_utc.tz_convert(ABT)
    return pd.DataFrame({
        "hour_start_utc": hours_utc,
        "price_date": pd.Timestamp(target_date),
        "hour_ending": local.hour + 1,
        "day_of_week": local.dayofweek + 1,   # Monday = 1 ... Sunday = 7
        "month": local.month,
        "year": local.year,
        "pool_price": float("nan"),          # unknown: this is what we predict
    })


# ---------- 2. Small database helpers ----------
def already_done(conn, target_date):
    count = conn.execute(
        "SELECT count(*) FROM forecasts WHERE forecast_date = %s AND model_name = %s",
        (target_date, MODEL_NAME),
    ).fetchone()[0]
    return count > 0


def save(conn, today):
    rows = [
        (r.hour_start_utc.to_pydatetime(), r.price_date.date(), int(r.hour_ending),
         round(float(r.predicted_price), 2), MODEL_NAME)
        for r in today.itertuples()
    ]
    with conn.transaction():
        conn.cursor().executemany(
            "INSERT INTO forecasts "
            "(forecast_for_utc, forecast_date, hour_ending, predicted_price, model_name) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (forecast_for_utc, model_name) DO NOTHING",
            rows,
        )


# ---------- 3. Main ----------
def main():
    target_date = datetime.now(ABT).date()
    target_ts = pd.Timestamp(target_date)

    with psycopg.connect(DATABASE_URL) as conn:
        if already_done(conn, target_date):
            print(f"Forecast for {target_date} already saved. Nothing to do.")
            return

        # Only data known by midnight: everything before today
        history = load_data()
        history["hour_start_utc"] = pd.to_datetime(history["hour_start_utc"], utc=True)
        history = history[history["price_date"] < target_ts]

        # Is yesterday complete? Last hour must be 23:00-24:00 yesterday, with a final price.
        future = future_hours(target_date)
        last = history.iloc[-1]
        expected_last = future["hour_start_utc"].iloc[0] - pd.Timedelta(hours=1)
        if last["hour_start_utc"] != expected_last or pd.isna(last["pool_price"]):
            print(f"Yesterday's prices are not all in yet (last hour: {last['hour_start_utc']}). "
                  "Will try again on the next run.")
            return

        # Features for history + the 24 new hours together (so lags line up)
        combined = pd.concat([history, future], ignore_index=True).sort_values("hour_start_utc")
        combined = add_features(combined, drop_missing=False)

        train = combined[combined["price_date"] < target_ts].dropna(subset=["pool_price"] + FEATURES)
        today = combined[combined["price_date"] == target_ts].copy()

        # Same model settings as train.py
        model = lgb.LGBMRegressor(objective="l1", n_estimators=500, learning_rate=0.05,
                                  num_leaves=31, random_state=42, verbose=-1)
        model.fit(train[FEATURES], train["pool_price"])
        today["predicted_price"] = model.predict(today[FEATURES]).clip(min=0)

        save(conn, today)

    print(f"Saved forecast for {target_date} ({len(today)} hours), trained on {len(train):,} hours:")
    print(today[["hour_ending", "lag_24", "predicted_price"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()