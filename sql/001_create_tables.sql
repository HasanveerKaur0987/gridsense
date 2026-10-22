-- Raw data, saved as AESO sends it (only cast to the right types)
CREATE TABLE IF NOT EXISTS raw_pool_price (
    begin_datetime_utc   TIMESTAMPTZ PRIMARY KEY,  -- one row per hour, no duplicates
    begin_datetime_mpt   TIMESTAMP   NOT NULL,     -- Alberta local time (kept for checks)
    pool_price           NUMERIC(10,2),            -- NULL until the hour is final
    forecast_pool_price  NUMERIC(10,2),
    rolling_30day_avg    NUMERIC(10,2),
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A log of every time the pipeline runs
CREATE TABLE IF NOT EXISTS ingest_runs (
    run_id         SERIAL PRIMARY KEY,
    source         TEXT        NOT NULL,           -- e.g. 'pool_price'
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    start_date     DATE,
    end_date       DATE,
    rows_fetched   INT,
    rows_inserted  INT,
    rows_updated   INT,
    status         TEXT        NOT NULL DEFAULT 'running',  -- running / success / failed
    error_message  TEXT
);

SELECT COUNT(*) FROM raw_pool_price;