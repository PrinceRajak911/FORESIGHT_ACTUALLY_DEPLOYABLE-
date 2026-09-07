
from pathlib import Path
import json
import pandas as pd
import numpy as np
import json

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

REQUIRED = {
    "sales_daily.csv": ["date","sku_id","units_sold","revenue","unit_price","promo_flag"],
    "sku_master.csv": ["sku_id","category","subcategory","launch_date","unit_cost","list_price"],
    "calendar.csv": ["date","week","month","season","is_holiday","promo_event"],
    "inventory_snapshots.csv": ["date","sku_id","on_hand_units","on_order_units","lead_time_days","reorder_point"],
}

def validate_schema():
    issues = []
    for filename, cols in REQUIRED.items():
        path = RAW / filename
        if not path.exists():
            issues.append(f"Missing file: {filename}")
            continue
        df = pd.read_csv(path, nrows=5)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            issues.append(f"{filename}: missing columns {missing}")
    return issues

def clean_data():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    issues = validate_schema()
    if issues:
        raise ValueError("; ".join(issues))

    sales = pd.read_csv(RAW/"sales_daily.csv", parse_dates=["date"])
    sku = pd.read_csv(RAW/"sku_master.csv", parse_dates=["launch_date"])
    cal = pd.read_csv(RAW/"calendar.csv", parse_dates=["date"])
    inv = pd.read_csv(RAW/"inventory_snapshots.csv", parse_dates=["date"])

    report = {
        "raw_sales_rows": int(len(sales)),
        "raw_sku_rows": int(len(sku)),
        "raw_calendar_rows": int(len(cal)),
        "raw_inventory_rows": int(len(inv)),
        "duplicate_sales_rows_removed": int(sales.duplicated(subset=["date","sku_id"]).sum()),
    }

    sales = sales.drop_duplicates(subset=["date","sku_id"], keep="first")
    sales["units_sold"] = pd.to_numeric(sales["units_sold"], errors="coerce").fillna(0).clip(lower=0)
    sales["revenue"] = pd.to_numeric(sales["revenue"], errors="coerce").fillna(0).clip(lower=0)
    sales["unit_price"] = pd.to_numeric(sales["unit_price"], errors="coerce")
    sales["unit_price"] = sales["unit_price"].fillna(sales.groupby("sku_id")["unit_price"].transform("median"))
    sales["unit_price"] = sales["unit_price"].fillna(sales["unit_price"].median())
    sales["promo_flag"] = pd.to_numeric(sales["promo_flag"], errors="coerce").fillna(0).astype(int)

    for col in ["category","subcategory"]:
        sku[col] = sku[col].astype(str).str.strip().str.title()
    sku["unit_cost"] = pd.to_numeric(sku["unit_cost"], errors="coerce")
    sku["list_price"] = pd.to_numeric(sku["list_price"], errors="coerce")
    sku["unit_cost"] = sku["unit_cost"].fillna(sku["unit_cost"].median())
    sku["list_price"] = sku["list_price"].fillna(sku["list_price"].median())

    cal["season"] = cal["season"].astype(str).str.strip().str.title()
    cal["promo_event"] = cal["promo_event"].fillna("None").astype(str).str.strip()
    cal["is_holiday"] = pd.to_numeric(cal["is_holiday"], errors="coerce").fillna(0).astype(int)

    inv["on_hand_units"] = pd.to_numeric(inv["on_hand_units"], errors="coerce").fillna(0).clip(lower=0)
    inv["on_order_units"] = pd.to_numeric(inv["on_order_units"], errors="coerce").fillna(0).clip(lower=0)
    inv["lead_time_days"] = pd.to_numeric(inv["lead_time_days"], errors="coerce").fillna(7).clip(lower=1)
    inv["reorder_point"] = pd.to_numeric(inv["reorder_point"], errors="coerce").fillna(0).clip(lower=0)

    sales.to_csv(PROCESSED/"sales_clean.csv", index=False)
    sku.to_csv(PROCESSED/"sku_master_clean.csv", index=False)
    cal.to_csv(PROCESSED/"calendar_clean.csv", index=False)
    inv.to_csv(PROCESSED/"inventory_clean.csv", index=False)

    report.update({
        "clean_sales_rows": int(len(sales)),
        "clean_sku_rows": int(len(sku)),
        "clean_calendar_rows": int(len(cal)),
        "clean_inventory_rows": int(len(inv)),
        "sales_missing_price_after_clean": int(sales["unit_price"].isna().sum()),
        "inventory_missing_values_after_clean": int(inv.isna().sum().sum()),
    })
    (PROCESSED/"data_quality.json").write_text(json.dumps(report, indent=2))
    return report

def build_analysis_ready():
    clean_data()
    sales = pd.read_csv(PROCESSED/"sales_clean.csv", parse_dates=["date"])
    sku = pd.read_csv(PROCESSED/"sku_master_clean.csv", parse_dates=["launch_date"])
    cal = pd.read_csv(PROCESSED/"calendar_clean.csv", parse_dates=["date"])

    df = sales.merge(sku, on="sku_id", how="left", validate="many_to_one")
    df = df.merge(cal, on="date", how="left", validate="many_to_one")
    df["gross_margin_per_unit"] = df["unit_price"] - df["unit_cost"]
    df["gross_margin"] = df["gross_margin_per_unit"] * df["units_sold"]
    df.to_csv(PROCESSED/"analysis_ready.csv", index=False)
    return df

if __name__ == "__main__":
    build_analysis_ready()
    print("Analysis-ready dataset created.")
