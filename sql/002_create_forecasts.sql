-- Forecasts made by the model, one row per hour per model
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_for_utc  TIMESTAMPTZ   NOT NULL,
    forecast_date     DATE          NOT NULL,
    hour_ending       INT           NOT NULL,
    predicted_price   NUMERIC(10,2) NOT NULL,
    model_name        TEXT          NOT NULL DEFAULT 'lightgbm_v1',
    made_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
    PRIMARY KEY (forecast_for_utc, model_name)
);

-- The public dashboard user may read it (but not change it)
GRANT SELECT ON forecasts TO dashboard_reader;