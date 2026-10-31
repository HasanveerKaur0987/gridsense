"""Tests for forecast/features.py: lags, yesterday's numbers, weekend flag.

Run from the gridsense folder:
    pytest
"""
import numpy as np
import pandas as pd

from features import FEATURES, add_features


def fake_prices(days=10, start="2026-10-01"):
    """Hourly rows like load_data() returns. Price = row number, so lags are easy to check."""
    n = days * 24
    dates = pd.date_range(start, periods=days, freq="D").repeat(24)
    return pd.DataFrame({
        "hour_start_utc": pd.date_range(f"{start} 06:00", periods=n, freq="h", tz="UTC"),
        "price_date": dates,
        "hour_ending": np.tile(np.arange(1, 25), days),
        "day_of_week": dates.dayofweek + 1,   # Monday = 1 ... Sunday = 7
        "month": dates.month,
        "year": dates.year,
        "pool_price": np.arange(n, dtype=float),
    })


def test_lags_point_to_the_right_hour():
    df = add_features(fake_prices(), drop_missing=False)
    row = df.iloc[200]
    assert row["lag_24"] == row["pool_price"] - 24
    assert row["lag_48"] == row["pool_price"] - 48
    assert row["lag_168"] == row["pool_price"] - 168


def test_first_rows_have_no_lag():
    df = add_features(fake_prices(), drop_missing=False)
    assert df["lag_24"].iloc[:24].isna().all()
    assert df["lag_168"].iloc[:168].isna().all()


def test_prev_day_avg_and_max_come_from_yesterday():
    df = add_features(fake_prices(), drop_missing=False)
    day2 = df[df["price_date"] == "2026-10-02"]
    # Day 1 prices are 0..23: average 11.5, max 23
    assert (day2["prev_day_avg"] == 11.5).all()
    assert (day2["prev_day_max"] == 23).all()


def test_no_peeking_at_today():
    """Changing today's prices must not change any of today's features."""
    prices = fake_prices()
    changed = prices.copy()
    last_day = changed["price_date"] == changed["price_date"].max()
    changed.loc[last_day, "pool_price"] = 999.0

    before = add_features(prices, drop_missing=False)[last_day.values]
    after = add_features(changed, drop_missing=False)[last_day.values]
    pd.testing.assert_frame_equal(before[FEATURES], after[FEATURES])


def test_is_weekend():
    df = add_features(fake_prices(), drop_missing=False)
    saturdays = df[df["day_of_week"] == 6]
    wednesdays = df[df["day_of_week"] == 3]
    assert (saturdays["is_weekend"] == 1).all()
    assert (wednesdays["is_weekend"] == 0).all()


def test_drop_missing_removes_first_week():
    df = add_features(fake_prices(days=10))
    assert len(df) == 3 * 24                    # 10 days - 7 days without lag_168
    assert not df[FEATURES].isna().any().any()
