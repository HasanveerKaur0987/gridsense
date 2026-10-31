"""Week 4, step 2: train a LightGBM model and compare it with the baselines.

Run from the gridsense folder:
    python forecast/train.py
"""
import lightgbm as lgb
import pandas as pd

from features import FEATURES, add_features, load_data

# ---------- 1. Data ----------
data = add_features(load_data())

# Time-based split: learn from the past, test on the future (never shuffle!)
SPLIT_DATE = pd.Timestamp("2025-07-01")
TRAIN_START = pd.Timestamp("2023-01-08")
train = data[(data["price_date"] >= TRAIN_START) & (data["price_date"] < SPLIT_DATE)]
test = data[data["price_date"] >= SPLIT_DATE].copy()

print(f"Train: {train['price_date'].min():%Y-%m-%d} to {train['price_date'].max():%Y-%m-%d} "
      f"({len(train):,} hours)")
print(f"Test:  {test['price_date'].min():%Y-%m-%d} to {test['price_date'].max():%Y-%m-%d} "
      f"({len(test):,} hours)")


# ---------- 2. Train the model ----------
model = lgb.LGBMRegressor(
    objective="l1",      # learn to make the MAE small (good when there are spikes)
    n_estimators=500,    # number of small trees
    learning_rate=0.05,  # how big each learning step is
    num_leaves=31,       # how detailed each tree can be
    random_state=42,     # same result every run
    verbose=-1,          # no extra messages
)
model.fit(train[FEATURES], train["pool_price"])


# ---------- 3. Predict the test period ----------
test["model_pred"] = model.predict(test[FEATURES])


# ---------- 4. Grade every forecast with MAE (smaller = better) ----------
def mae(real, guess):
    return (real - guess).abs().mean()


results = pd.DataFrame({
    "MAE ($)": [
        mae(test["pool_price"], test["model_pred"]),
        mae(test["pool_price"], test["lag_24"]),
        mae(test["pool_price"], test["lag_168"]),
    ]
}, index=["LightGBM model", "Same as yesterday", "Same as last week"]).round(2)

print("\nTest results:")
print(results.to_string())

best_baseline = results.loc["Same as yesterday", "MAE ($)"]
model_mae = results.loc["LightGBM model", "MAE ($)"]
better_pct = 100 * (best_baseline - model_mae) / best_baseline
print(f"\nModel is {better_pct:.1f}% better than 'same as yesterday'")


# ---------- 5. Which clues did the model use most? ----------
importance = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
print("\nFeature importance (how often each clue was used):")
print(importance.to_string())


# ---------- 6. Where does the model miss: normal vs spike hours ----------
test["err_model"] = (test["pool_price"] - test["model_pred"]).abs()
test["err_yesterday"] = (test["pool_price"] - test["lag_24"]).abs()

test["hour_type"] = "normal (< $100)"
test.loc[test["pool_price"] >= 100, "hour_type"] = "spike ($100+)"

by_type = test.groupby("hour_type").agg(
    hours=("err_model", "size"),
    model_mae=("err_model", "mean"),
    yesterday_mae=("err_yesterday", "mean"),
    total_error=("err_model", "sum"),
)
by_type["share_of_hours_%"] = 100 * by_type["hours"] / by_type["hours"].sum()
by_type["share_of_error_%"] = 100 * by_type["total_error"] / by_type["total_error"].sum()

print("\nNormal vs spike hours:")
print(by_type.drop(columns="total_error").round(1).to_string())