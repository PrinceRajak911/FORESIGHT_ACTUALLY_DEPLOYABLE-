# FORESIGHT — Executive Readout

## Business problem
Reduce stockouts while avoiding excess inventory. The solution forecasts weekly SKU demand and turns the forecast into transparent inventory actions.

## Data
Four extracts: daily sales, SKU master, calendar and inventory snapshots. The raw synthetic data deliberately contains small quality issues so the cleaning layer is demonstrable.

## Forecasting
Weekly SKU demand uses lag, rolling, calendar, season and promotion features. A seasonal-naive forecast is the mandatory baseline. Evaluation uses rolling-origin backtesting, WAPE and bias.

## Backtest
- Seasonal-naive WAPE: 21.6%
- Random Forest WAPE: 24.5%
- Selected production forecast: **seasonal_naive**
- Model bias: 13.46 units/week
- Baseline bias: 3.66 units/week

The baseline won on this seeded dataset, so the system ships the baseline rather than fabricating an ML win.

## Inventory risk
- High stockout risk SKUs: 31
- High overstock risk SKUs: 24
- Capital locked: ₹58,972,740
- Revenue exposure: ₹9,966,591

## Product
Streamlit provides category/SKU filtering, prioritised action lists and forecast views. FastAPI exposes `/health`, `/metrics` and `/score`.

## Limitations / next steps
Synthetic data; productionisation should add formal service-level probability, prediction intervals, sparse/new-SKU fallback, known future promotion feeds, drift monitoring and a production database.
