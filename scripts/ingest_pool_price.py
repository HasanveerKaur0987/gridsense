"""Load AESO pool prices into Neon (the real pipeline).

How to run (from the gridsense folder):
    python scripts/ingest_pool_price.py
        -> hourly mode: loads yesterday + today (what GitHub Actions will run)

    python scripts/ingest_pool_price.py --start 2023-01-01 --end 2026-10-21
        -> backfill mode: loads that date range, one month at a time

Safe to run again and again: an hour that is already saved is never added twice.
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
import requests
from dotenv import load_dotenv

# ---------- 1. Settings ----------
load_dotenv()
API_KEY = os.getenv("AESO_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
if not API_KEY or not DATABASE_URL:
    raise SystemExit("AESO_API_KEY or DATABASE_URL is missing. Put them in your .env file.")

URL = "https://apimgw.aeso.ca/public/poolprice-api/v1.1/price/poolPrice"
ALBERTA = ZoneInfo("America/Edmonton")  # AESO dates are Alberta dates


# ---------- 2. Get data from AESO ----------
def fetch(start, end):
    """Download rows for these Alberta dates (end date included)."""
    resp = requests.get(URL, headers={"API-KEY": API_KEY},
                        params={"startDate": start.isoformat(), "endDate": end.isoformat()},
                        timeout=60)
    resp.raise_for_status()  # stop with an error if status is not 200
    return resp.json()["return"]["Pool Price Report"]


# ---------- 3. Clean one row ----------
def to_number(value):
    """'45.21' -> Decimal('45.21'), and '' or None -> None (saved as NULL)."""
    if value is None or str(value).strip() == "":
        return None
    return Decimal(str(value))


def clean(row):
    """Turn one AESO row (all text) into the right Python types for the table."""
    return (
        datetime.fromisoformat(row["begin_datetime_utc"]).replace(tzinfo=timezone.utc),
        datetime.fromisoformat(row["begin_datetime_mpt"]),
        to_number(row["pool_price"]),
        to_number(row["forecast_pool_price"]),
        to_number(row["rolling_30day_avg"]),
    )


# ---------- 4. Save to the database ----------
# Add the hour. If the hour is already there, update it ONLY if a value changed.
# RETURNING tells us what happened:
#   True  -> new hour (loaded_at = updated_at, both just set)
#   False -> old hour that changed (updated_at is new, loaded_at is old)
#   no row back -> old hour, nothing changed
UPSERT_SQL = """
INSERT INTO raw_pool_price
    (begin_datetime_utc, begin_datetime_mpt, pool_price, forecast_pool_price, rolling_30day_avg)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (begin_datetime_utc) DO UPDATE SET
    begin_datetime_mpt  = EXCLUDED.begin_datetime_mpt,
    pool_price          = EXCLUDED.pool_price,
    forecast_pool_price = EXCLUDED.forecast_pool_price,
    rolling_30day_avg   = EXCLUDED.rolling_30day_avg,
    updated_at          = now()
WHERE (raw_pool_price.pool_price, raw_pool_price.forecast_pool_price, raw_pool_price.rolling_30day_avg)
      IS DISTINCT FROM
      (EXCLUDED.pool_price, EXCLUDED.forecast_pool_price, EXCLUDED.rolling_30day_avg)
RETURNING (loaded_at = updated_at) AS is_new
"""


def save(conn, rows):
    """Save all rows. Returns (inserted, updated)."""
    inserted = updated = 0
    with conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, rows, returning=True)  # sends all rows in one go
        while True:
            result = cur.fetchone()
            if result is not None:
                if result[0]:
                    inserted += 1
                else:
                    updated += 1
            if not cur.nextset():
                break
    return inserted, updated


# ---------- 5. The diary (ingest_runs) ----------
def start_run(conn, start, end):
    row = conn.execute(
        "INSERT INTO ingest_runs (source, start_date, end_date) "
        "VALUES ('pool_price', %s, %s) RETURNING run_id",
        (start, end),
    ).fetchone()
    return row[0]


def finish_run(conn, run_id, status, fetched=None, inserted=None, updated=None, error=None):
    conn.execute(
        "UPDATE ingest_runs SET finished_at = now(), status = %s, rows_fetched = %s, "
        "rows_inserted = %s, rows_updated = %s, error_message = %s WHERE run_id = %s",
        (status, fetched, inserted, updated, error, run_id),
    )


# ---------- 6. One run = one date range ----------
def ingest(conn, start, end):
    """Load one date range and write one line in the diary. Returns True if it worked."""
    run_id = start_run(conn, start, end)
    try:
        rows = [clean(r) for r in fetch(start, end)]
        with conn.transaction():  # all rows are saved, or none are
            inserted, updated = save(conn, rows)
        finish_run(conn, run_id, "success", len(rows), inserted, updated)
        print(f"{start} -> {end}: fetched {len(rows)}, new {inserted}, updated {updated}")
        return True
    except Exception as e:
        finish_run(conn, run_id, "failed", error=str(e)[:1000])
        print(f"{start} -> {end}: FAILED: {e}")
        return False


def month_chunks(start, end):
    """Split a date range into pieces of one month: Jan 1-31, Feb 1-28, ..."""
    while start <= end:
        next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
        chunk_end = min(next_month - timedelta(days=1), end)
        yield start, chunk_end
        start = next_month


# ---------- 7. Main ----------
def main():
    parser = argparse.ArgumentParser(description="Load AESO pool prices into Neon.")
    parser.add_argument("--start", type=date.fromisoformat, help="first date, like 2023-01-01")
    parser.add_argument("--end", type=date.fromisoformat, help="last date, like 2026-10-21")
    args = parser.parse_args()

    today = datetime.now(ALBERTA).date()  # Alberta's today (GitHub's computers use UTC)
    if args.start:
        chunks = list(month_chunks(args.start, args.end or today))   # backfill mode
    else:
        chunks = [(today - timedelta(days=1), today)]               # hourly mode

    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        for start, end in chunks:
            if not ingest(conn, start, end):
                sys.exit(1)  # stop, so GitHub Actions shows a red X


if __name__ == "__main__":
    main()