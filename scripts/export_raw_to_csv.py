"""Export raw PostgreSQL tables to CSV using pandas."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd


RAW_TABLES = [
    "cities",
    "categories",
    "products",
    "payment_methods",
    "shipping_services",
    "vouchers",
    "customer_profile_events",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "order_status_events",
]


def connection_uri() -> str:
    host = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "retail_dw"))
    user = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "dwbi"))
    password = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "dwbi"))
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export raw tables to CSV files.")
    parser.add_argument("--output-dir", default="data/exports")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    uri = connection_uri()

    for table in RAW_TABLES:
        df = pd.read_sql_query(f"select * from raw.{table}", uri)
        file_path = output_dir / f"{table}.csv"
        df.to_csv(file_path, index=False)
        print(f"exported raw.{table}: {len(df)} rows -> {file_path}")


if __name__ == "__main__":
    main()
