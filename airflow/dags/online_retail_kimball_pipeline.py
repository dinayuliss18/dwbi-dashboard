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