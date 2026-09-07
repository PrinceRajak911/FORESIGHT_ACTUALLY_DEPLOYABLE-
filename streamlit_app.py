
from pathlib import Path
import json, sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"
MODELS = ROOT/"models"

st.set_page_config(page_title="FORESIGHT | Inventory Planning", layout="wide")

@st.cache_data
def load_all():
    sku = pd.read_csv(DATA/"sku_master_clean.csv")
    weekly = pd.read_csv(DATA/"weekly_demand.csv", parse_dates=["week_start"])
    forecast = pd.read_csv(DATA/"forecast_6w.csv", parse_dates=["week_start"])
    risk = pd.read_csv(DATA/"risk_scores.csv")
    metrics = json.loads((MODELS/"metrics.json").read_text())
    return sku, weekly, forecast, risk, metrics

st.title("FORESIGHT")
st.caption("Demand Forecasting & Inventory Risk Planning")

try:
    sku, weekly, forecast, risk, metrics = load_all()
except Exception as e:
    st.error("The model artifacts are missing. Run `python src/run_pipeline.py` first.")
    st.exception(e)
    st.stop()

risk = risk.merge(sku[["sku_id","category","subcategory","unit_cost","list_price"]], on="sku_id", how="left")
categories = ["All"] + sorted(sku["category"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Category", categories)
selected_sku = st.sidebar.selectbox("SKU", ["All"] + sorted(sku["sku_id"].tolist()))

view = risk.copy()
if selected_cat != "All":
    view = view[view["category"] == selected_cat]
if selected_sku != "All":
    view = view[view["sku_id"] == selected_sku]

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("SKUs", f"{len(view):,}")
c2.metric("High Stockout", f"{(view.stockout_risk=='HIGH').sum():,}")
c3.metric("High Overstock", f"{(view.overstock_risk=='HIGH').sum():,}")
c4.metric("Capital Locked", f"₹{view.capital_locked.sum()/1e5:.1f}L")
c5.metric("Revenue at Risk", f"₹{view.revenue_at_risk.sum()/1e5:.1f}L")

tab1, tab2, tab3 = st.tabs(["Planning", "Forecast", "Model Validation"])

with tab1:
    st.subheader("Prioritised inventory actions")
    order = view[view.action=="REORDER NOW"].sort_values("revenue_at_risk", ascending=False)
    clear = view[view.action=="MARKDOWN / CLEAR"].sort_values("capital_locked", ascending=False)
    st.write("### Reorder now")
    st.dataframe(order[["sku_id","category","lead_time_demand","on_hand_units","on_order_units","revenue_at_risk","action"]], use_container_width=True)
    st.write("### Markdown / clear")
    st.dataframe(clear[["sku_id","category","forecast_6w_demand","on_hand_units","excess_units","capital_locked","action"]], use_container_width=True)

with tab2:
    st.subheader("Forecast vs actual")
    sku_choice = selected_sku if selected_sku != "All" else st.selectbox("Choose a SKU", sorted(sku["sku_id"].tolist()))
    hist = weekly[weekly.sku_id.eq(sku_choice)].tail(52)
    fc = forecast[forecast.sku_id.eq(sku_choice)]
    chart = pd.DataFrame({
        "Actual": hist.set_index("week_start")["units_sold"],
        "Forecast": fc.set_index("week_start")["forecast"]
    })
    st.line_chart(chart)
    st.dataframe(fc[["week_start","forecast"]], use_container_width=True)

with tab3:
    st.subheader("Backtest")
    st.write("The model is selected only if it beats the seasonal-naive baseline on WAPE.")
    m1,m2,m3 = st.columns(3)
    m1.metric("Seasonal-naive WAPE", f"{metrics['baseline_wape']:.1%}")
    m2.metric("Model WAPE", f"{metrics['ml_wape']:.1%}")
    m3.metric("Selected", metrics["selected_model"])
    st.write("Bias (forecast − actual)")
    st.write({
        "Seasonal naive": metrics["baseline_bias"],
        "Model": metrics["ml_bias"]
    })
    st.info("WAPE is the primary metric because low-volume SKUs make MAPE unstable.")
