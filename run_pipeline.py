
from pathlib import Path
import json, pickle
from data_pipeline import build_analysis_ready
from forecasting import train_and_backtest, generate_selected_forecast
from risk_engine import build_risk_table

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"
MODELS = ROOT/"models"

def main():
    print("1/4 Cleaning and validating data...")
    build_analysis_ready()

    print("2/4 Training and rolling-origin backtest...")
    weekly, model, metrics = train_and_backtest()

    print("3/4 Generating six-week forecast...")
    forecast = generate_selected_forecast(weekly, model, metrics, horizon=6)
    forecast.to_csv(DATA/"forecast_6w.csv", index=False)

    print("4/4 Scoring inventory risk...")
    risk = build_risk_table(forecast)
    risk.to_csv(DATA/"risk_scores.csv", index=False)

    summary = {
        "selected_model": metrics["selected_model"],
        "baseline_wape": metrics["baseline_wape"],
        "model_wape": metrics["ml_wape"],
        "high_stockout_skus": int((risk.stockout_risk=="HIGH").sum()),
        "high_overstock_skus": int((risk.overstock_risk=="HIGH").sum()),
        "capital_locked": float(risk.capital_locked.sum()),
        "revenue_at_risk": float(risk.revenue_at_risk.sum()),
    }
    (MODELS/"run_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
