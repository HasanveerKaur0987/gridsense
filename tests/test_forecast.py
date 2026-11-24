from predict_today import future_hours
import pandas as pd
from features import add_features


# Helper: a fake week of prices (not a test, because the name doesn't start with test_)
def make_fake_prices():
    hours = pd.date_range("2026-01-05", periods=168, freq="h")  # 7 days, starting Monday
    return pd.DataFrame({
        "price_date": hours.normalize(),     # the date of each hour
        "day_of_week": hours.day_of_week + 1,  # Monday = 1 ... Sunday = 7
        "pool_price": range(168),            # price = row number (0, 1, 2, ...)
    })


# Test 1: future_hours makes the 24 hours of one Alberta day
def test_future_hours_makes_24_hours():
    hours = future_hours("2026-12-01")
    assert len(hours) == 24
    assert hours["hour_ending"].iloc[0] == 1
    assert hours["hour_ending"].iloc[-1] == 24
    assert hours["hour_start_utc"].iloc[0].hour == 6   # midnight in Alberta = 6 AM UTC


# Test 2: lag_24 is the price from exactly 24 hours earlier
def test_lag_24_is_price_24_hours_ago():
    df = add_features(make_fake_prices(), drop_missing=False)
    assert df["lag_24"].iloc[30] == 6                  # 30 - 24 = 6
    assert df["lag_24"].iloc[:24].isna().all()         # first day has no "yesterday"


# Test 3: day_of_week is always between 1 and 7
def test_day_of_week_is_1_to_7():
    df = add_features(make_fake_prices(), drop_missing=False)
    assert df["day_of_week"].between(1, 7).all()


# Test 4: is_weekend is 1 only on Saturday (6) and Sunday (7)
def test_is_weekend_only_on_saturday_and_sunday():
    df = add_features(make_fake_prices(), drop_missing=False)
    weekend_days = df[df["is_weekend"] == 1]["day_of_week"].unique()
    assert sorted(weekend_days) == [6, 7]