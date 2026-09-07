
from pathlib import Path
import json, pickle
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"
MODELS = ROOT/"models"

app = FastAPI(title="FORESIGHT Scoring API", version="1.0.0")

class ScoreRequest(BaseModel):
    sku_id: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "foresight-scoring-api"}

@app.get("/metrics")
def metrics():
    return json.loads((MODELS/"metrics.json").read_text())

@app.post("/score")
def score(req: ScoreRequest):
    risk_path = DATA/"risk_scores.csv"
    fc_path = DATA/"forecast_6w.csv"
    if not risk_path.exists() or not fc_path.exists():
        raise HTTPException(503, "Model artifacts are not available. Run the pipeline first.")

    risk = pd.read_csv(risk_path)
    fc = pd.read_csv(fc_path, parse_dates=["week_start"])
    row = risk[risk.sku_id.eq(req.sku_id)]
    if row.empty:
        raise HTTPException(404, f"Unknown SKU: {req.sku_id}")

    r = row.iloc[0]
    f = fc[fc.sku_id.eq(req.sku_id)].sort_values("week_start").head(6)

    return {
        "sku_id": req.sku_id,
        "forecast_6_weeks": [
            {"week_start": str(x.week_start.date()), "forecast_units": round(float(x.forecast),2)}
            for x in f.itertuples()
        ],
        "inventory": {
            "on_hand_units": float(r.on_hand_units),
            "on_order_units": float(r.on_order_units),
            "lead_time_days": int(r.lead_time_days),
            "reorder_point": float(r.reorder_point)
        },
        "risk": {
            "stockout": r.stockout_risk,
            "overstock": r.overstock_risk,
            "action": r.action,
            "capital_locked": float(r.capital_locked),
            "revenue_at_risk": float(r.revenue_at_risk)
        }
    }
