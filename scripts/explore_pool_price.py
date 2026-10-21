"""Look closely at AESO pool price data before designing tables (pandas version).

Checks: missing hours, empty prices, price range, and the DST (clock change) day.
Nothing is saved. It only prints.
"""
import os
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("AESO_API_KEY")
if not key:
    raise SystemExit("AESO_API_KEY is missing. Put it in your .env file.")

URL = "https://apimgw.aeso.ca/public/poolprice-api/v1.1/price/poolPrice"


def fetch(start, end):
    """Download rows from AESO and return them as a pandas DataFrame."""
    resp = requests.get(URL, headers={"API-KEY": key},
                        params={"startDate": start, "endDate": end}, timeout=60)
    if resp.status_code != 200:
        print(resp.text[:500])
        raise SystemExit(f"Request failed with status {resp.status_code}")
    df = pd.DataFrame(resp.json()["return"]["Pool Price Report"])

    # AESO sends everything as text. Turn it into real times and numbers.
    df["begin_datetime_utc"] = pd.to_datetime(df["begin_datetime_utc"], utc=True)
    for col in ["pool_price", "forecast_pool_price", "rolling_30day_avg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")  # empty text -> NaN
    return df


# 1) One full month: are all hours there?
print("=== 1) October 2025 ===")
df = fetch("2025-10-01", "2025-10-31")
print("Rows:", len(df), "(expected 31 * 24 = 744)")
print(df.head(3))
print("\nColumn types:\n", df.dtypes)

steps = df["begin_datetime_utc"].diff().dropna()
gaps = df.loc[steps.index[steps != pd.Timedelta(hours=1)], "begin_datetime_utc"]
print("\nGaps or repeats in UTC:", list(gaps) or "none")
print("Duplicate UTC hours:", df["begin_datetime_utc"].duplicated().sum())

print("\nEmpty values per column:\n", df.isna().sum())
print("\nPrice summary:\n", df["pool_price"].describe().round(2))

# 2) The day the clocks go back (DST ended Nov 2, 2025)
print("\n=== 2) DST day: Nov 2, 2025 ===")
dst = fetch("2025-11-02", "2025-11-02")
print("Rows:", len(dst), "(should be 25, one hour repeats)")
print(dst[["begin_datetime_utc", "begin_datetime_mpt"]].head(5).to_string(index=False))

# 3) Today: what do hours that haven't happened yet look like?
print("\n=== 3) Today (last 3 rows) ===")
today = datetime.now().strftime("%Y-%m-%d")
print(fetch(today, today).tail(3).to_string(index=False))