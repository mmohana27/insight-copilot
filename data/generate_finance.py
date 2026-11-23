"""Generate synthetic finance data based on real Olist sales and load it into the raw schema.

Everything here is SYNTHETIC. The seed is fixed, so re-running gives identical data.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

rng = np.random.default_rng(42)  # fixed seed = reproducible data

# Months with meaningful Olist volume
START_YM, END_YM = 201701, 201808

COST_RATES = {  # cost type -> (min, max) share of monthly revenue
    "cost_of_goods": (0.55, 0.65),
    "marketing": (0.06, 0.09),
    "logistics_overhead": (0.03, 0.05),
    "platform_tech": (0.02, 0.03),
    "customer_support": (0.02, 0.04),
    "payroll": (0.12, 0.16),
}

CAMPAIGNS = [
    ("Summer Sale 2017", "email", "2017-01-16", "2017-01-31", "ALL", 18000),
    ("Carnival Fashion Push", "social", "2017-02-20", "2017-03-05", "RJ", 12500),
    ("Mothers Day 2017", "search", "2017-05-01", "2017-05-14", "ALL", 30000),
    ("Winter Home Refresh", "influencer", "2017-06-15", "2017-07-10", "SP", 22000),
    ("Fathers Day 2017", "email", "2017-08-01", "2017-08-13", "ALL", 16000),
    ("Childrens Day 2017", "social", "2017-10-01", "2017-10-12", "ALL", 14000),
    ("Black Friday 2017", "search", "2017-11-20", "2017-11-27", "ALL", 85000),
    ("Christmas 2017", "tv", "2017-12-01", "2017-12-20", "ALL", 60000),
    ("New Year Electronics", "email", "2018-01-08", "2018-01-31", "SP", 20000),
    ("Carnival 2018", "social", "2018-02-05", "2018-02-14", "RJ", 15000),
    ("Mothers Day 2018", "search", "2018-04-28", "2018-05-13", "ALL", 38000),
    ("World Cup 2018", "tv", "2018-06-10", "2018-07-14", "ALL", 70000),
    ("Back to Basics Brand", "influencer", "2018-07-20", "2018-08-20", "MG", 24000),
]


def get_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


def actual_revenue(engine) -> pd.DataFrame:
    sql = """
        select f.purchase_year, f.purchase_month, p.category, sum(f.price) as revenue
        from marts.fct_sales f
        join marts.dim_products p on p.product_id = f.product_id
        group by 1, 2, 3
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    df["revenue"] = df["revenue"].astype(float)
    ym = df["purchase_year"] * 100 + df["purchase_month"]
    return df[(ym >= START_YM) & (ym <= END_YM)].reset_index(drop=True)


def make_budget(rev: pd.DataFrame) -> pd.DataFrame:
    # Budget = actual revenue +/- 20%, so there is a realistic over/under-budget story
    out = rev.copy()
    out["budget_revenue"] = (out["revenue"] * rng.uniform(0.80, 1.20, len(out))).round(2)
    return out.rename(
        columns={"purchase_year": "fiscal_year", "purchase_month": "fiscal_month"}
    )[["fiscal_year", "fiscal_month", "category", "budget_revenue"]]


def make_costs(rev: pd.DataFrame) -> pd.DataFrame:
    monthly = rev.groupby(["purchase_year", "purchase_month"], as_index=False)["revenue"].sum()
    rows = []
    for r in monthly.itertuples(index=False):
        for cost_type, (lo, hi) in COST_RATES.items():
            rows.append({
                "fiscal_year": r.purchase_year,
                "fiscal_month": r.purchase_month,
                "cost_type": cost_type,
                "amount": round(float(r.revenue) * rng.uniform(lo, hi), 2),
            })
    return pd.DataFrame(rows)


def make_campaigns() -> pd.DataFrame:
    rows = [
        {
            "campaign_id": f"C{i:03d}", "campaign_name": name, "channel": channel,
            "start_date": start, "end_date": end, "target_state": state, "spend": spend,
        }
        for i, (name, channel, start, end, state, spend) in enumerate(CAMPAIGNS, start=1)
    ]
    return pd.DataFrame(rows)


def load(engine, df: pd.DataFrame, table: str) -> None:
    df = df.astype(str)  # raw = as arrived (text); dbt staging will type it
    df["_source_file"] = "synthetic_generator"
    df["_loaded_at"] = pd.Timestamp.now(tz="UTC")
    df.to_sql(table, engine, schema="raw", if_exists="replace", index=False, method="multi")
    print(f"raw.{table:<22} {len(df):>8,} rows")


def main():
    engine = get_engine()
    rev = actual_revenue(engine)
    print(f"Actual revenue rows (month x category): {len(rev):,}\n")
    load(engine, make_budget(rev), "budget")
    load(engine, make_costs(rev), "operating_costs")
    load(engine, make_campaigns(), "marketing_campaigns")
    print("\nDone.")


if __name__ == "__main__":
    main()