from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os

DATA_DIR = os.getenv("AIRFLOW_INPUT_DIR", "/opt/airflow/sample_files")
TELEMETRY_FILE = os.path.join(DATA_DIR, "telemetry_db_table.csv")
CRM_FILE = os.path.join(DATA_DIR, "crm_table.csv")


def extract_telemetry(**context):
    import csv

    rows = []
    with open(TELEMETRY_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "user_id":   int(row["user_id"]),
                "device_id": int(row["device_id"]),
                "event_type": row["event_type"],
            })

    context["ti"].xcom_push(key="telemetry_rows", value=rows)


def extract_crm(**context):
    import csv

    users = set()
    with open(CRM_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.add(int(row["user_id"]))

    context["ti"].xcom_push(key="crm_users", value=list(users))


def transform(**context):
    ti = context["ti"]
    telemetry_rows = ti.xcom_pull(key="telemetry_rows", task_ids="extract_telemetry")
    crm_users      = set(ti.xcom_pull(key="crm_users",      task_ids="extract_crm"))

    aggregated = {}
    for row in telemetry_rows:
        user_id   = row["user_id"]
        device_id = row["device_id"]

        if user_id not in crm_users:
            continue

        key = (user_id, device_id)
        aggregated[key] = aggregated.get(key, 0) + 1

    result = [
        {"user_id": uid, "device_id": did, "action_count": cnt}
        for (uid, did), cnt in aggregated.items()
    ]

    ti.xcom_push(key="report_rows", value=result)


def load_to_dwh(**context):
    import psycopg2

    rows = context["ti"].xcom_pull(key="report_rows", task_ids="transform")

    if not rows:
        print("No rows to insert")
        return

    conn = psycopg2.connect(
        host="airflow_db",
        port=5432,
        dbname="sample",
        user="airflow",
        password="airflow",
    )
    cursor = conn.cursor()

    for row in rows:
        if isinstance(row, dict):
            user_id = row.get("user_id", "")
            device_id = row.get("device_id", "")

            query = f"""
            SELECT action_count 
            FROM user_report
            WHERE user_id = '{str(user_id)}' AND device_id = '{str(device_id)}'
            """
            cursor.execute(query=query)
            res = cursor.fetchone()
            
            if res:
                cursor.execute(
                f"""
                UPDATE user_report
                SET action_count = {str(row.get("action_count", res[2]))}
                WHERE user_id = '{str(user_id)}' AND device_id = '{str(device_id)}'
                """
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_report (user_id, device_id, action_count)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        str(row.get("user_id")),
                        str(row.get("device_id")),
                        str(row.get("action_count"))
                    )
                )

    # cursor.executemany("""
    #     INSERT INTO user_report (user_id, device_id, action_count)
    #     VALUES (%(user_id)s, %(device_id)s, %(action_count)s)
    #     ON CONFLICT (user_id, device_id)
    #     DO UPDATE SET action_count = user_report.action_count + EXCLUDED.action_count
    # """, rows)

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Inserted {len(rows)} rows into user_report")


with DAG(
    dag_id="user_report_etl",
    start_date=datetime(2024, 1, 1),
    schedule_interval="*/15 * * * *",
    catchup=False,
) as dag:

    t1 = PythonOperator(task_id="extract_telemetry", python_callable=extract_telemetry)
    t2 = PythonOperator(task_id="extract_crm",       python_callable=extract_crm)
    t3 = PythonOperator(task_id="transform",          python_callable=transform)
    t4 = PythonOperator(task_id="load_to_dwh",        python_callable=load_to_dwh)

    [t1, t2] >> t3 >> t4


if __name__ == "__main__":

    load_to_dwh()