"""Tests for forecast/predict_today.py: the 24 hours we forecast.

Run from the gridsense folder:
    pytest
"""
from datetime import date

import pandas as pd

from predict_today import future_hours


def test_future_hours_makes_24_hours_from_6am_utc():
    hours = future_hours(date(2026, 11, 2))
    assert len(hours) == 24
    assert hours["hour_start_utc"].iloc[0] == pd.Timestamp("2026-11-02 06:00", tz="UTC")
    assert hours["hour_start_utc"].iloc[-1] == pd.Timestamp("2026-11-03 05:00", tz="UTC")
    assert list(hours["hour_ending"]) == list(range(1, 25))


def test_future_hours_all_on_the_same_alberta_day():
    target = date(2026, 11, 2)                  # a Monday
    hours = future_hours(target)
    assert (hours["price_date"] == pd.Timestamp(target)).all()
    assert (hours["day_of_week"] == 1).all()    # Monday = 1, like isodow
    assert (hours["month"] == 11).all()


def test_nov_1_2026_has_24_hours():
    """Alberta stopped changing clocks: Nov 1, 2026 is a normal 24-hour day."""
    hours = future_hours(date(2026, 11, 1))
    assert len(hours) == 24
    assert list(hours["hour_ending"]) == list(range(1, 25))


def test_prices_are_unknown():
    assert future_hours(date(2026, 11, 2))["pool_price"].isna().all()
