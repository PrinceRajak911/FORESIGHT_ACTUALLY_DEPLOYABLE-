
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"

def build_risk_table(forecast, horizon=6):
    inv = pd.read_csv(DATA/"inventory_clean.csv", parse_dates=["date"])
    sku = pd.read_csv(DATA/"sku_master_clean.csv")
    latest_date = inv["date"].max()
    inv = inv[inv["date"].eq(latest_date)].copy()

    fc = forecast.copy()
    fc["week_start"] = pd.to_datetime(fc["week_start"])

    rows = []
    for r in inv.itertuples(index=False):
        f = fc[fc["sku_id"].eq(r.sku_id)].sort_values("week_start").head(horizon)
        if f.empty:
            continue

        daily_rate = max(float(f["forecast"].mean()/7), 0.01)
        lead_weeks = max(1, int(np.ceil(r.lead_time_days/7)))
        lead_demand = float(f.head(lead_weeks)["forecast"].sum())
        horizon_demand = float(f["forecast"].sum())
        available = float(r.on_hand_units + r.on_order_units)
        stock_gap = lead_demand - available

        # Transparent thresholds rather than a black-box classifier.
        stockout_risk = (
            "HIGH" if stock_gap > 0 else
            "MEDIUM" if available < lead_demand * 1.25 else
            "LOW"
        )

        excess_units = max(0.0, float(r.on_hand_units) - horizon_demand)
        sku_cost = float(sku.loc[sku["sku_id"].eq(r.sku_id), "unit_cost"].iloc[0])
        locked_capital = excess_units * sku_cost
        overstock_risk = (
            "HIGH" if excess_units > max(10, horizon_demand * .50) else
            "MEDIUM" if excess_units > max(5, horizon_demand * .20) else
            "LOW"
        )

        if stockout_risk == "HIGH" and overstock_risk != "HIGH":
            action = "REORDER NOW"
        elif overstock_risk == "HIGH" and stockout_risk != "HIGH":
            action = "MARKDOWN / CLEAR"
        elif stockout_risk == "HIGH" and overstock_risk == "HIGH":
            action = "WATCH"
        else:
            action = "HEALTHY"

        # Conservative value-at-stake: lost-sales exposure is forecast demand not covered by available stock.
        lost_units = max(0.0, stock_gap)
        unit_price = float(sku.loc[sku["sku_id"].eq(r.sku_id), "list_price"].iloc[0])
        revenue_at_risk = lost_units * unit_price

        rows.append({
            "sku_id": r.sku_id,
            "on_hand_units": r.on_hand_units,
            "on_order_units": r.on_order_units,
            "lead_time_days": r.lead_time_days,
            "reorder_point": r.reorder_point,
            "lead_time_demand": round(lead_demand,2),
            "forecast_6w_demand": round(horizon_demand,2),
            "stock_gap": round(stock_gap,2),
            "stockout_risk": stockout_risk,
            "excess_units": round(excess_units,2),
            "capital_locked": round(locked_capital,2),
            "overstock_risk": overstock_risk,
            "revenue_at_risk": round(revenue_at_risk,2),
            "action": action,
        })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    import pickle
    import json
    from forecasting import make_weekly, generate_selected_forecast
    with open(ROOT/"models/forecast_model.pkl","rb") as f:
        model = pickle.load(f)
    weekly = pd.read_csv(DATA/"weekly_demand.csv", parse_dates=["week_start"])
    metrics = json.loads((ROOT/"models/metrics.json").read_text())
    fc = generate_selected_forecast(weekly, model, metrics, 6)
    risk = build_risk_table(fc)
    risk.to_csv(DATA/"risk_scores.csv", index=False)
    print(risk.head())
