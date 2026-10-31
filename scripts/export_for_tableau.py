"""Save GridSense data as CSV files for Tableau Public."""
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing. Put it in your .env file.")

out_folder = Path(__file__).parent.parent / "exports"
out_folder.mkdir(exist_ok=True)

# file name -> SQL query
QUERIES = {
    "hourly_prices.csv": """
        select hour_start_mpt, price_date,
               hour_ending::int as hour_ending,
               day_of_week::int as day_of_week,
               month::int as month, year::int as year,
               pool_price, forecast_pool_price
        from analytics.stg_pool_price
        where pool_price is not null
        order by hour_start_utc
    """,
    "daily_prices.csv": """
        select * from analytics.daily_prices
        where is_complete
        order by price_date
    """,
}

with psycopg.connect(url) as conn:
    for file_name, sql in QUERIES.items():
        cur = conn.execute(sql)
        columns = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)
        df.to_csv(out_folder / file_name, index=False)
        print(f"{file_name}: {len(df)} rows")