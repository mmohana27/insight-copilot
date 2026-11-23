"""Load the Olist CSV files into the Postgres `raw` schema, exactly as they arrive."""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
load_dotenv(ROOT / ".env")

# CSV file name -> table name in the raw schema
FILES = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_translation",
}

CHUNK_SIZE = 50_000


def get_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    return create_engine(url)


def load_table(engine, csv_name: str, table: str) -> int:
    path = RAW_DIR / csv_name
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    total = 0
    # dtype=str keeps every value exactly as it arrived (typing happens later, in staging)
    for i, chunk in enumerate(pd.read_csv(path, dtype=str, chunksize=CHUNK_SIZE)):
        chunk["_source_file"] = csv_name                   # lineage: where did this row come from?
        chunk["_loaded_at"] = pd.Timestamp.now(tz="UTC")   # lineage: when was it loaded?
        chunk.to_sql(
            table,
            engine,
            schema="raw",
            if_exists="replace" if i == 0 else "append",   # first chunk resets the table
            index=False,
            method="multi",
        )
        total += len(chunk)
    return total


def main():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))  # fail fast if the DB is unreachable
    print("Connected to Postgres.\n")

    for csv_name, table in FILES.items():
        rows = load_table(engine, csv_name, table)
        print(f"raw.{table:<30} {rows:>10,} rows")

    print("\nDone.")


if __name__ == "__main__":
    main()