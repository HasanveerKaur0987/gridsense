"""GridSense dashboard: Alberta electricity prices (Streamlit).

Run from the gridsense folder:
    streamlit run dashboard/app.py
"""
import os
from decimal import Decimal
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv

# ---------- 1. Settings ----------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") or st.secrets["DATABASE_URL"]
ALBERTA = ZoneInfo("America/Edmonton")

st.set_page_config(page_title="GridSense", page_icon="⚡", layout="wide")


# ---------- 2. Get data from Neon ----------
@st.cache_data(ttl=600)  # remember results for 10 minutes
def run_query(sql):
    """Run a SQL query in Neon and return a pandas table."""
    with psycopg.connect(DATABASE_URL) as conn:
        cur = conn.execute(sql)
        columns = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columns)

    # Neon sends numbers as Decimal; charts need normal numbers (float)
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


DAILY_SQL = """
    select price_date, avg_price, min_price, max_price, is_complete
    from analytics.daily_prices
    order by price_date
"""

HOURLY_SQL = """
    select year::int as year,
           hour_ending::int as hour_ending,
           round(avg(pool_price), 2) as avg_price
    from analytics.stg_pool_price
    where pool_price is not null
    group by year, hour_ending
    order by year, hour_ending
"""

YEARLY_SQL = """
    select year::int as year,
           round(avg(pool_price), 2) as avg_price,
           round((percentile_cont(0.5) within group (order by pool_price))::numeric, 2) as median_price,
           round(100.0 * count(*) filter (where pool_price >= 100) / count(*), 1) as spike_pct
    from analytics.stg_pool_price
    where pool_price is not null
    group by year
    order by year
"""

LAST_RUN_SQL = """
    select max(finished_at) as last_run
    from public.ingest_runs
    where status = 'success'
"""

daily = run_query(DAILY_SQL)
hourly = run_query(HOURLY_SQL)
yearly = run_query(YEARLY_SQL)
last_run = run_query(LAST_RUN_SQL)["last_run"].iloc[0]

# Only finished days for averages and charts
complete = daily[daily["is_complete"]].copy()
complete["price_date"] = pd.to_datetime(complete["price_date"])
complete["rolling_7d"] = complete["avg_price"].rolling(7, min_periods=1).mean().round(2)


# ---------- 3. Header ----------
st.title("GridSense ⚡")
st.write("Alberta electricity pool prices from AESO, updated every hour.")

if last_run is not None:
    last_run_local = pd.Timestamp(last_run).tz_convert(ALBERTA)
    st.caption(f"Last updated: {last_run_local:%b %d, %Y at %I:%M %p} (Alberta time)")


# ---------- 4. Top numbers ----------
yesterday = complete.iloc[-1]
day_before = complete.iloc[-2]
latest_year = yearly.iloc[-1]
latest_year_num = int(latest_year["year"])

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    f"Avg price, {yesterday['price_date']:%b %d}",
    f"${yesterday['avg_price']:.2f}",
    f"{yesterday['avg_price'] - day_before['avg_price']:+.2f} vs day before",
    delta_color="inverse",  # price going up shows red
)
c2.metric("7-day average", f"${yesterday['rolling_7d']:.2f}")
c3.metric(f"Typical hour in {latest_year_num} (median)", f"${latest_year['median_price']:.2f}")
c4.metric(f"Spike hours in {latest_year_num} ($100+)", f"{latest_year['spike_pct']:.1f}%")

st.divider()


# ---------- 5. Chart: daily price + 7-day average ----------
st.subheader("Daily average price")

period = st.radio("Show", ["Last 90 days", "Last year", "All data"], horizontal=True)
days_back = {"Last 90 days": 90, "Last year": 365, "All data": len(complete)}[period]
recent = complete.tail(days_back)

st.line_chart(
    recent.set_index("price_date")[["avg_price", "rolling_7d"]],
    y_label="$/MWh",
)
st.caption("The 7-day average smooths out spike days so the trend is easier to see.")


# ---------- 6. Chart: price by hour of day ----------
left, right = st.columns(2)

with left:
    st.subheader("Price by hour of day")
    years = sorted(hourly["year"].unique(), reverse=True)
    year = st.selectbox("Year", years)
    one_year = hourly[hourly["year"] == year]
    st.bar_chart(one_year.set_index("hour_ending")["avg_price"], y_label="Avg $/MWh")
    st.caption("Hour ending 20 = 7–8 PM. Evenings cost the most: high demand and no solar.")


# ---------- 7. Chart: spikes and average vs median per year ----------
with right:
    st.subheader("Spike hours per year")
    yearly_chart = yearly.copy()
    yearly_chart["year"] = yearly_chart["year"].astype(str)
    st.bar_chart(yearly_chart.set_index("year")["spike_pct"], y_label="% of hours at $100+")
    st.caption("Spike hours dropped from about 28% of hours in 2023 to under 4% in 2026.")

st.subheader("Average vs typical (median) price")
st.dataframe(
    yearly.rename(columns={
        "year": "Year",
        "avg_price": "Average ($/MWh)",
        "median_price": "Median ($/MWh)",
        "spike_pct": "Spike hours (%)",
    }),
    hide_index=True,
)
st.caption("A few spike hours pull the average up to about 2x the median, "
           "so the median shows a more normal price.")

st.divider()


# ---------- 8. Findings ----------
st.subheader("Key findings")
st.markdown("""
- **Evenings are the most expensive.** 7–8 PM averages about 4x the price of 3–4 AM.
- **Price spikes almost disappeared.** About 1 in 4 hours were $100+ in 2023; in 2026 it's about 1 in 26.
- **Weekends are cheaper every year**, by 14% to 43%.
- **The January 2024 cold snap** was the most expensive week in the data (Jan 11–17, about $420/day).
- **The average misleads.** It is about 2x the median every year because of a few spike hours.
""")

with st.expander("How this works"):
    st.markdown("""
- **Data:** AESO public API (pool price), Jan 2023 to now.
- **Pipeline:** Python + GitHub Actions load new hours into PostgreSQL (Neon) every hour.
  Each run re-loads yesterday and today, so missed runs never leave gaps.
- **Cleaning:** dbt models (`stg_pool_price`, `daily_prices`) with 6 data tests
  (no duplicates, no missing hours, prices between $0 and $999.99).
- **Times:** stored in UTC to avoid daylight saving problems, shown in Alberta time.
""")