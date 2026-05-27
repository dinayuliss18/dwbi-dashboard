# Online Retail Order Management Data Warehouse

University project for Data Warehouse & Business Intelligence using Kimball dimensional modeling (Master of Computer Science UGM).

The business is an online retail store selling products directly to customers across 34 cities in Indonesia.

## Tech Stack

| Tool | Use |
| --- | --- |
| PostgreSQL | Raw, staging, intermediate, and analytics warehouse schemas |
| Python Faker | Realistic synthetic customer/order data |
| Pandas | DataFrame generation and CSV export |
| dbt | ELT, dimensional modeling (37 models: 1 incremental, 19 tables, 17 views), tests, and documentation |
| Apache Airflow | Pipeline orchesration (Init and Incremental architectures) |
| Docker Compose | Local environment virtualization |
| Metabase | BI Dashboard and Native Query analytics |

## Quick Start

```bash
docker compose up -d --build postgres airflow-init airflow-webserver airflow-scheduler
```

Open the Apache Airflow UI in your browser:

```text
URL: http://localhost:8080
Username: admin
Password: admin
```
Pipeline Execution:
Bootstrap Initial Load (Required First): Manually trigger the online_retail_init DAG. This DAG generates 60,000 historical transaction rows spanning from 2022 to May 25, 2026, executes a schema drop, and builds all dbt transformation models cleanly using the --full-refresh flag.

Automated Scheduled Delta Stream: Activate (Toggle ON) the online_retail_incremental DAG. This pipeline runs automatically every 6 hours (0 */6 * * *) to check for incoming operational data, simulates the ingestion of 500 new daily orders, and triggers a dbt MERGE incremental strategy on the fact layer.

Connect Metabase (Enable the Metabase profile via Docker if needed):
```bash
docker compose --profile metabase up -d metabase
```

## Folder Structure

```text
.
├── airflow/dags/online_retail_kimball_pipeline.py
├── data/exports/
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── macros/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   │       ├── dimensions/
│   │       ├── facts/
│   │       └── analytics/
│   └── tests/
├── docker/
├── docs/
├── scripts/
├── sql/
└── docker-compose.yml
```

## Business Requirements Analysis

The warehouse must support revenue, city, product, payment, voucher, shipping, cancellation, return, peak-hour, and profitability analysis.

Key analytical requirements:

| Requirement | Supported by |
| --- | --- |
| Monthly revenue trend | `mart_monthly_revenue` |
| City transactions and revenue | `mart_city_performance` |
| Product performance and returns | `mart_product_performance` |
| Payment method usage and value | `mart_payment_method_performance` |
| Shipping usage, delay, fastest/slowest service | `mart_shipping_performance` |
| Peak order hours | `mart_hourly_orders` |
| Promo loss and profit margin | `mart_monthly_revenue`, `fct_order_item` |

## Stakeholder Analysis

| Stakeholder | Questions |
| --- | --- |
| Executives | Revenue, profit, margin, growth trend |
| Marketing | Voucher assignment, customer groups, payment promotions |
| Merchandising | Top products, high-profit low-sales categories, return rates |
| Operations | Shipping provider performance, delays, cancellation stages |
| Finance | Discount, voucher, shipping subsidy loss and profit impact |
| Customer Experience | Delivery duration, return/cancellation patterns |

## Business Processes

| Process | Description |
| --- | --- |
| Customer ordering | Customers buy one or more products in an order |
| Payment | Orders are paid by E-wallet, QRIS, COD, or Paylater |
| Voucher usage | Vouchers are assigned based on eligibility and payment method |
| Shipping | Multiple shipping providers deliver orders |
| Order status tracking | Orders move through placed, paid, packed, shipped, delivered, cancelled, returned |
| Returns and cancellations | Orders/items can be cancelled or returned |

## Dimensional Model

Core fact table:

```text
analytics.fct_order_item
```

Grain:

```text
One row represents one product item purchased in a single customer order transaction.
```

Required dimensions:

| Dimension | Purpose |
| --- | --- |
| `dim_customer` | SCD2 customer profile and address history |
| `dim_product` | Product SKU, product name, price, estimated cost |
| `dim_category` | Category and subcategory |
| `dim_payment_method` | E-wallet, QRIS, COD, Paylater |
| `dim_shipping` | Shipping provider and service |
| `dim_order_status` | Order lifecycle status |
| `dim_voucher` | Voucher rules and payment eligibility |
| `dim_city` | 34 Indonesian cities |
| `dim_date` | Calendar role-playing dimension |
| `dim_time` | Time-of-day role-playing dimension |

See [docs/star_schema.md](docs/star_schema.md) for the schema diagram and design decisions.

## Required Fact Measures

`fct_order_item` includes:

| Measure | Meaning |
| --- | --- |
| `quantity` | Units purchased |
| `unit_price` | Product selling price per unit |
| `subtotal` | Quantity times unit price before promotions |
| `discount_amount` | Item-level product discount |
| `shipping_subsidy` | Shipping discount allocated to the item |
| `voucher_amount` | Voucher discount allocated to the item |
| `total_payment` | Amount paid by customer for the item |
| `estimated_cost` | Estimated product cost |
| `profit` | `total_payment - estimated_cost - shipping_subsidy` |
| `delivery_duration_minutes` | Checkout to delivery duration |
| `is_returned` | Return flag |
| `is_cancelled` | Cancellation flag |

## SCD Type 2

Customer address changes are generated in `raw.customer_profile_events`.

`int_customer_scd2` builds valid date ranges using `lead(effective_at)`. `dim_customer` stores historical customer versions and the fact table joins to the version active at order time.

This allows accurate historical reporting by customer city and loyalty tier.

## Synthetic Data

Generator:

```text
scripts/generate_synthetic_data.py
```

Features:

| Feature |
| --- |
| At least 12,000 order item transactions by default |
| 34 Indonesian cities |
| Order dates from 2022 through 2026 by default |
| Peak-season demand around major Indonesian religious holidays |
| Skewed product popularity distribution |
| Payment methods: E-wallet, QRIS, COD, Paylater |
| Voucher categories: no discount, cashback 10% min 200k, free ongkir min 50k, electronics direct discount 100k |
| Delayed shipping scenarios |
| Cancelled and returned orders |
| Customer address changes for SCD2 |
| Realistic pricing, cost, and margin |
| CSV export using Pandas |

## dbt Layers

| Layer | Path | Purpose |
| --- | --- | --- |
| Staging | `dbt/models/staging` | Clean source tables |
| Intermediate | `dbt/models/intermediate` | SCD2, lifecycle, fulfillment, enrichment |
| Dimensions | `dbt/models/marts/dimensions` | Star schema dimensions |
| Facts | `dbt/models/marts/facts` | Atomic fact table |
| Analytics marts | `dbt/models/marts/analytics` | BI-ready tables |

## Manual dbt Execution via Docker Container

```bash
# Rebuild the complete dimensional model mapping (Staging -> Facts -> Marts)
docker exec -it retail_dw_airflow_webserver dbt run --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

# Execute all 135 built-in dbt data quality and structural integrity tests
docker exec -it retail_dw_airflow_webserver dbt test --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

# Compile the data lineage graph and launch the static documentation schema
docker exec -it retail_dw_airflow_webserver dbt docs generate --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
```

## Tests and Data Quality

dbt includes:

| Test |
| --- |
| not_null and unique tests for surrogate keys |
| relationship tests between fact and dimensions |
| accepted values for payment methods and order statuses |
| minimum 10,000 order item rows |
| fact grain uniqueness |
| SCD2 overlap prevention |
| one current customer version |
| amount formula validation |
| profit formula validation |
| 34-city dimension validation |

Additional validation SQL is in [sql/data_quality_validation.sql](sql/data_quality_validation.sql).

## Analytical SQL

The file [sql/analytical_queries.sql](sql/analytical_query.sql) 
