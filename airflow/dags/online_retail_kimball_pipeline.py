"""Airflow DAGs — Online Retail Kimball Pipeline

Two DAGs are defined here:

1. online_retail_init
   ─────────────────
   Run ONCE to bootstrap the warehouse.
   • Generates the full historical dataset with generate_synthetic_data.py
     (seed mode — truncate-free, uses CREATE TABLE IF NOT EXISTS).
   • Runs dbt debug → dbt run → dbt test → dbt docs generate.
   • Trigger manually (schedule=None).  Never re-run unless you want to
     wipe and rebuild from scratch (requires manual TRUNCATE first).

2. online_retail_incremental
   ─────────────────────────
   Runs on a schedule (every 6 hours by default).
   • Checks whether new rows landed in raw.orders since the last watermark.
   • If new data is present → runs dbt run (incremental models only) +
     dbt test + dbt docs generate.
   • If no new data → skips gracefully via AirflowSkipException.
   • The new-data simulation step (append_new_orders) is a separate task
     that you can disable once a real source system feeds the raw layer.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator, ShortCircuitOperator

DBT_DIR     = "/opt/airflow/dbt"
SCRIPTS_DIR = "/opt/airflow/scripts"

default_args = {
    "owner":           "dwbi-team",
    "depends_on_past": False,
    "retries":         1,
    "retry_delay":     timedelta(minutes=3),
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: detect whether new rows have landed since the last pipeline run.
# Returns True  → ShortCircuitOperator lets downstream tasks proceed.
# Returns False → ShortCircuitOperator skips all downstream tasks.
# ─────────────────────────────────────────────────────────────────────────────
def _has_new_data(**context) -> bool:
    """Return True if raw.orders contains rows loaded after the last
    pipeline watermark recorded for the 'orders' table."""
    import os
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost")),
        port=int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "retail_dw")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "dwbi")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "dwbi")),
    )
    try:
        with conn.cursor() as cur:
            # Watermark = the loaded_at of the last successful dbt run
            # (stored under the special key '_dbt_last_run').
            cur.execute(
                """
                select coalesce(
                    (select last_loaded_at
                       from raw._pipeline_watermark
                      where table_name = '_dbt_last_run'),
                    '1970-01-01'::timestamp
                )
                """
            )
            last_dbt_run: datetime = cur.fetchone()[0]

            cur.execute(
                "select count(*) from raw.orders where loaded_at > %s",
                (last_dbt_run,),
            )
            new_rows: int = cur.fetchone()[0]

        has_new = new_rows > 0
        print(
            f"[detect_new_data] last dbt run: {last_dbt_run} | "
            f"new raw.orders rows: {new_rows} → {'PROCEED' if has_new else 'SKIP'}"
        )
        return has_new
    finally:
        conn.close()


def _stamp_dbt_run(**context) -> None:
    """After a successful dbt run, update the watermark so the next
    pipeline execution knows where this run ended."""
    import os
    from datetime import datetime
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "localhost")),
        port=int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", "5432"))),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "retail_dw")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "dwbi")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "dwbi")),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into raw._pipeline_watermark (table_name, last_loaded_at)
                values ('_dbt_last_run', %s)
                on conflict (table_name) do update
                    set last_loaded_at = excluded.last_loaded_at
                """,
                (datetime.utcnow(),),
            )
        conn.commit()
        print("[stamp_dbt_run] Watermark updated.")
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════════════════════
# DAG 1 — INIT  (run once, manually triggered)
# ═════════════════════════════════════════════════════════════════════════════
with DAG(
    dag_id="online_retail_init",
    description=(
        "ONE-TIME bootstrap: generate full historical seed data, then build "
        "the Kimball warehouse with dbt. Trigger manually; do not schedule."
    ),
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,          # manual trigger only
    catchup=False,
    max_active_runs=1,
    tags=["dwbi", "kimball", "retail", "dbt", "init"],
) as init_dag:

    seed_raw_data = BashOperator(
        task_id="seed_raw_data",
        bash_command=(
            f"python {SCRIPTS_DIR}/generate_synthetic_data.py "
            "--mode seed "
            "--orders 60000 "
            "--end-date 2026-05-25 "
            "--min-items ${MIN_ORDER_ITEMS:-12000} "
            "--customers ${CUSTOMER_COUNT:-2500} "
            "--products ${PRODUCT_COUNT:-350} "
            "--export-csv "
            "--csv-dir /opt/airflow/data/exports"
        ),
        doc_md=(
            "Generate the full historical dataset and load it into raw.* tables. "
            "Uses `--mode seed` which calls `CREATE TABLE IF NOT EXISTS` and "
            "`INSERT … ON CONFLICT DO NOTHING` for dimension tables. "
            "Run this task only once."
        ),
    )

    dbt_debug_init = BashOperator(
        task_id="dbt_debug",
        bash_command=f"cd {DBT_DIR} && dbt debug --profiles-dir {DBT_DIR} || true",
    )

    dbt_run_init = BashOperator(
        task_id="dbt_run",
        # Ditambahkan --full-refresh di akhir string command
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir {DBT_DIR} --full-refresh",
        doc_md="Full dbt run — builds all models from scratch on first load.",
    )

    dbt_test_init = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir {DBT_DIR}",
    )

    dbt_docs_init = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_DIR} && dbt docs generate --profiles-dir {DBT_DIR}",
    )

    stamp_init = PythonOperator(
        task_id="stamp_dbt_watermark",
        python_callable=_stamp_dbt_run,
        doc_md="Record the current UTC timestamp as the dbt watermark so the "
               "incremental DAG knows where the init run ended.",
    )

    export_raw_csv_init = BashOperator(
        task_id="export_raw_csv",
        bash_command=(
            f"python {SCRIPTS_DIR}/export_raw_to_csv.py "
            "--output-dir /opt/airflow/data/exports || true"
        ),
    )

    (
        seed_raw_data
        >> dbt_debug_init
        >> dbt_run_init
        >> dbt_test_init
        >> dbt_docs_init
        >> stamp_init
    )
    seed_raw_data >> export_raw_csv_init
    
# ═════════════════════════════════════════════════════════════════════════════
# DAG 2 — INCREMENTAL  (runs on schedule, skips when no new data)
# ═════════════════════════════════════════════════════════════════════════════
with DAG(
    dag_id="online_retail_incremental",
    description=(
        "Scheduled incremental pipeline. Simulates new orders arriving, "
        "detects them, and triggers dbt incremental models only when new "
        "raw data is present."
    ),
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule="0 */6 * * *",   # every 6 hours — adjust to match your SLA
    catchup=False,
    max_active_runs=1,
    tags=["dwbi", "kimball", "retail", "dbt", "incremental"],
) as incremental_dag:

    # ── Step 0: Simulate new orders arriving in the raw layer ─────────────
    # In production, replace this task with your real ingestion mechanism
    # (Kafka consumer, S3 trigger, CDC from OLTP, etc.).
    simulate_new_orders = BashOperator(
        task_id="simulate_new_orders",
        bash_command=(
            f"python {SCRIPTS_DIR}/generate_synthetic_data.py "
            "--mode append "
            "--new-orders ${NEW_ORDER_COUNT:-500}"
        ),
        doc_md=(
            "Simulates new retail transactions being appended to raw.*. "
            "**Replace with your real ingestion task in production.** "
            "Uses `--mode append` → only INSERTs new transaction rows; "
            "dimension tables are not touched."
        ),
    )

    # ── Step 1: Check for new rows since last dbt run ─────────────────────
    detect_new_data = ShortCircuitOperator(
        task_id="detect_new_data",
        python_callable=_has_new_data,
        doc_md=(
            "Queries raw._pipeline_watermark to compare the last dbt run "
            "timestamp against MAX(loaded_at) in raw.orders. "
            "Returns True (proceed) only when new rows are found; "
            "otherwise short-circuits and skips all downstream tasks."
        ),
    )

# ── Step 2: dbt incremental run (only changed/new rows) ──────────────
    dbt_run_incremental = BashOperator(
        task_id="dbt_run_incremental",
        bash_command=(
            f"cd {DBT_DIR} && dbt run --profiles-dir {DBT_DIR} "
            "--select tag:incremental"  # <--- Hapus 'state:modified+' di sini
        ),
        doc_md=(
            "Runs only dbt models tagged `incremental`. The `fct_order_item` model "
            "must use `{{ config(materialized='incremental') }}` with `unique_key` "
            "and `incremental_strategy='merge'` for this to work correctly."
        ),
    )

    # ── Step 3: Data quality tests ────────────────────────────────────────
    dbt_test_incremental = BashOperator(
        task_id="dbt_test_incremental",
        bash_command=(
            f"cd {DBT_DIR} && dbt test --profiles-dir {DBT_DIR} "
            "--select tag:incremental"  # <--- Hapus 'state:modified+' di sini juga
        ),
    )

    # ── Step 4: Refresh docs ──────────────────────────────────────────────
    dbt_docs_incremental = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"cd {DBT_DIR} && dbt docs generate --profiles-dir {DBT_DIR}",
    )

    # ── Step 5: Advance the watermark ────────────────────────────────────
    stamp_incremental = PythonOperator(
        task_id="stamp_dbt_watermark",
        python_callable=_stamp_dbt_run,
        doc_md=(
            "Advances raw._pipeline_watermark['_dbt_last_run'] to NOW() so "
            "the next scheduled run only picks up rows loaded after this point."
        ),
    )

    (
        simulate_new_orders
        >> detect_new_data
        >> dbt_run_incremental
        >> dbt_test_incremental
        >> dbt_docs_incremental
        >> stamp_incremental
    )