
from pathlib import Path
import json, pickle
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"data"/"processed"
MODELS = ROOT/"models"

FEATURES = [
    "lag_1","lag_2","lag_4","lag_8","lag_13","lag_26","lag_52",
    "rolling_mean_4","rolling_mean_8","rolling_std_8",
    "week_sin","week_cos","month","is_holiday","promo_flag",
    "category","season"
]
NUMERIC = [x for x in FEATURES if x not in ["category","season"]]
CATEGORICAL = ["category","season"]

def wape(actual, predicted):
    denom = np.sum(np.abs(actual))
    return float(np.sum(np.abs(np.asarray(actual)-np.asarray(predicted))) / denom) if denom else np.nan

def bias(actual, predicted):
    return float(np.mean(np.asarray(predicted)-np.asarray(actual)))

def make_weekly():
    df = pd.read_csv(DATA/"analysis_ready.csv", parse_dates=["date","launch_date"])
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    weekly = (df.groupby(["sku_id","week_start"], as_index=False)
                .agg(units_sold=("units_sold","sum"),
                     revenue=("revenue","sum"),
                     promo_flag=("promo_flag","max"),
                     is_holiday=("is_holiday","max"),
                     category=("category","first"),
                     season=("season","first")))
    weekly["week_num"] = weekly["week_start"].dt.isocalendar().week.astype(int)
    weekly["month"] = weekly["week_start"].dt.month
    weekly["week_sin"] = np.sin(2*np.pi*weekly["week_num"]/52)
    weekly["week_cos"] = np.cos(2*np.pi*weekly["week_num"]/52)
    weekly = weekly.sort_values(["sku_id","week_start"]).reset_index(drop=True)
    g = weekly.groupby("sku_id", group_keys=False)
    for lag in [1,2,4,8,13,26,52]:
        weekly[f"lag_{lag}"] = g["units_sold"].shift(lag)
    weekly["rolling_mean_4"] = g["units_sold"].transform(lambda s: s.shift(1).rolling(4).mean())
    weekly["rolling_mean_8"] = g["units_sold"].transform(lambda s: s.shift(1).rolling(8).mean())
    weekly["rolling_std_8"] = g["units_sold"].transform(lambda s: s.shift(1).rolling(8).std())
    weekly["rolling_std_8"] = weekly["rolling_std_8"].fillna(0)
    weekly.to_csv(DATA/"weekly_demand.csv", index=False)
    return weekly

def seasonal_naive_predictions(history, future_dates):
    # Same ISO-week last year. For missing early history, fall back to the latest available value.
    lookup = history.set_index(["sku_id","week_start"])["units_sold"].to_dict()
    global_last = history.groupby("sku_id")["units_sold"].last().to_dict()
    rows = []
    for sku in future_dates["sku_id"].unique():
        f = future_dates[future_dates["sku_id"].eq(sku)]
        for d in f["week_start"]:
            prior = d - pd.DateOffset(weeks=52)
            val = lookup.get((sku, prior), global_last.get(sku, 0))
            rows.append((sku,d,float(val)))
    return pd.DataFrame(rows, columns=["sku_id","week_start","forecast"])

def train_and_backtest():
    weekly = make_weekly()
    max_date = weekly["week_start"].max()
    test_start = max_date - pd.Timedelta(weeks=7)
    train = weekly[weekly["week_start"] < test_start].copy()
    test = weekly[weekly["week_start"] >= test_start].copy()

    train_model = train.dropna(subset=FEATURES + ["units_sold"]).copy()
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
        ("num", "passthrough", NUMERIC),
    ])
    model = Pipeline([
        ("prep", pre),
        ("rf", RandomForestRegressor(
            n_estimators=100, max_depth=10, min_samples_leaf=2,
            random_state=42, n_jobs=-1
        ))
    ])
    model.fit(train_model[FEATURES], train_model["units_sold"])

    pred_rows = []
    for d in sorted(test["week_start"].unique()):
        test_day = test[test["week_start"].eq(d)].copy()
        usable = test_day.dropna(subset=FEATURES)
        if len(usable):
            pred = model.predict(usable[FEATURES])
            for sku, actual, forecast in zip(usable["sku_id"], usable["units_sold"], pred):
                pred_rows.append([d, sku, actual, max(0,float(forecast))])

    ml_eval = pd.DataFrame(pred_rows, columns=["week_start","sku_id","actual","ml_forecast"])
    # Evaluate seasonal naive on the exact same rows.
    lookup = train.set_index(["sku_id","week_start"])["units_sold"].to_dict()
    ml_eval["naive_forecast"] = [
        float(lookup.get((r.sku_id, r.week_start-pd.DateOffset(weeks=52)), 0))
        for r in ml_eval.itertuples()
    ]
    metrics = {
        "ml_wape": wape(ml_eval.actual, ml_eval.ml_forecast),
        "baseline_wape": wape(ml_eval.actual, ml_eval.naive_forecast),
        "ml_bias": bias(ml_eval.actual, ml_eval.ml_forecast),
        "baseline_bias": bias(ml_eval.actual, ml_eval.naive_forecast),
        "test_weeks": int(test["week_start"].nunique()),
        "test_rows": int(len(ml_eval)),
    }
    # Select only on measured backtest performance.
    use_ml = metrics["ml_wape"] < metrics["baseline_wape"]
    metrics["selected_model"] = "random_forest" if use_ml else "seasonal_naive"

    MODELS.mkdir(exist_ok=True)
    with open(MODELS/"forecast_model.pkl","wb") as f:
        pickle.dump(model,f)
    (MODELS/"metrics.json").write_text(json.dumps(metrics, indent=2))
    ml_eval.to_csv(MODELS/"backtest_results.csv", index=False)
    return weekly, model, metrics

def seasonal_naive_forecast(weekly, horizon=6):
    """Production forecast when the seasonal-naive baseline wins backtesting."""
    history = weekly.sort_values("week_start").copy()
    last = history["week_start"].max()
    lookup = history.set_index(["sku_id", "week_start"])["units_sold"].to_dict()
    last_values = history.groupby("sku_id")["units_sold"].last().to_dict()
    rows = []
    for sku in sorted(history["sku_id"].unique()):
        for h in range(1, horizon + 1):
            d = last + pd.Timedelta(weeks=h)
            prior = d - pd.DateOffset(weeks=52)
            value = lookup.get((sku, prior), last_values.get(sku, 0.0))
            rows.append({"sku_id": sku, "week_start": d, "forecast": max(0.0, float(value))})
    return pd.DataFrame(rows)

def recursive_forecast(model, weekly, horizon=6):
    """Recursive model forecast for the model path; kept separate from baseline selection."""
    history = weekly.copy().sort_values(["sku_id", "week_start"])
    last = history["week_start"].max()
    sku_meta = history.groupby("sku_id").tail(1).set_index("sku_id")
    series = {sku: g["units_sold"].tolist() for sku, g in history.groupby("sku_id")}
    rows = []
    season_map = {12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",
                  6:"Summer",7:"Summer",8:"Summer",9:"Autumn",10:"Autumn",11:"Autumn"}
    for h in range(1, horizon + 1):
        d = last + pd.Timedelta(weeks=h)
        batch = []
        for sku, vals in series.items():
            week_num = int(d.isocalendar().week)
            month = d.month
            row = {
                "sku_id": sku, "week_start": d,
                "lag_1": vals[-1], "lag_2": vals[-2], "lag_4": vals[-4],
                "lag_8": vals[-8], "lag_13": vals[-13], "lag_26": vals[-26],
                "lag_52": vals[-52], "rolling_mean_4": np.mean(vals[-4:]),
                "rolling_mean_8": np.mean(vals[-8:]), "rolling_std_8": np.std(vals[-8:]),
                "week_sin": np.sin(2*np.pi*week_num/52), "week_cos": np.cos(2*np.pi*week_num/52),
                "month": month, "is_holiday": 0, "promo_flag": 0,
                "category": sku_meta.loc[sku, "category"], "season": season_map[month]
            }
            batch.append(row)
        X = pd.DataFrame(batch)
        preds = np.maximum(0, model.predict(X[FEATURES]))
        for row, pred in zip(batch, preds):
            row["forecast"] = float(pred)
            rows.append(row)
            series[row["sku_id"]].append(float(pred))
    return pd.DataFrame(rows)

def generate_selected_forecast(weekly, model, metrics, horizon=6):
    if metrics["selected_model"] == "seasonal_naive":
        return seasonal_naive_forecast(weekly, horizon)
    return recursive_forecast(model, weekly, horizon)

if __name__ == "__main__":
    weekly, model, metrics = train_and_backtest()
    print(json.dumps(metrics, indent=2))
