# Project FORESIGHT

## Demand Forecasting & Inventory Risk Planning

FORESIGHT converts SKU-level sales history and inventory positions into:
1. a weekly demand forecast,
2. stockout/overstock risk,
3. a transparent recommended action,
4. a Streamlit planning dashboard, and
5. a FastAPI scoring service.

### Architecture

Raw extracts -> validation/cleaning -> analysis-ready data -> weekly features ->
seasonal-naive baseline + Random Forest -> rolling-origin backtest -> 6-week
forecast -> risk engine -> dashboard/API.

### Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python src/run_pipeline.py
streamlit run app/streamlit_app.py
```

API:
```bash
uvicorn service.api:app --reload --port 8000
```

Then open `/docs` on the API for the interactive OpenAPI interface.

### Why the project has multiple layers

- **Data pipeline:** client extracts are imperfect, so cleaning must be reproducible.
- **Weekly aggregation:** the brief asks for weekly SKU-level forecasting.
- **Seasonal-naive baseline:** prevents a complex model from being trusted without evidence.
- **Lag/rolling features:** give the global model recent momentum, seasonality and volatility.
- **Rolling-origin backtest:** respects the time ordering and avoids future leakage.
- **Risk engine:** turns a forecast into an operational decision rather than a prediction alone.
- **Rupee impact:** prioritises decisions by business consequence.
- **Streamlit:** makes the output usable by non-technical operations users.
- **FastAPI:** makes the scoring logic consumable by another system.

### Important methodological note

The model is not assumed to be better. `src/forecasting.py` measures both the model and
seasonal-naive baseline using WAPE and automatically records the selected model. If the
baseline wins, the system keeps the baseline rather than fabricating a win.

The synthetic data is only a development substitute for client extracts. It contains
deliberate data-quality issues so the cleaning layer can be demonstrated.

## Actual local deployment (Windows)

This repository is packaged to run directly on a Windows laptop.

### One-time setup

1. Install **Python 3.12.x**.
2. Extract this ZIP to a normal folder.
3. Double-click `setup.bat`.
4. Wait for the dependency installation and data/model pipeline to finish.

The setup script creates a local `venv`, installs `requirements.txt`, validates/cleans the included dataset, trains and backtests the forecasting model, generates the six-week forecast, and calculates inventory risk.

### Start the dashboard

Double-click:

`run_dashboard.bat`

Then open:

`http://localhost:8501`

### Start the scoring API

In a second terminal, run:

`run_api.bat`

API:

`http://localhost:8000`

Interactive API documentation:

`http://localhost:8000/docs`

### Re-run the complete pipeline

If you change the CSV files in `data/raw/`, run:

`run_pipeline.bat`

Then restart the dashboard.

## What is actually included

- The original FORESIGHT source code.
- The same raw and processed dataset supplied with this project.
- The trained model and backtest artifacts.
- Six-week forecasts and inventory risk scores.
- Streamlit dashboard.
- FastAPI scoring service.
- Docker configuration.
- Render deployment configuration.
- Windows setup/run scripts.

## Docker deployment

From the project root:

```bash
docker compose up --build
```

Dashboard: `http://localhost:8501`

API: `http://localhost:8000/docs`

To stop:

```bash
docker compose down
```

## Important project behavior

The forecasting pipeline compares the Random Forest model against a seasonal-naive baseline using WAPE. The model is used only when it wins the backtest; otherwise the seasonal-naive forecast is selected. This is intentional and makes the project defensible during an internship/project review.

The included dataset currently produces a seasonal-naive selection after backtesting. That is not an error: it means the more complex machine-learning model did not beat the baseline on the held-out period.
