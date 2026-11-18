import os
import sqlite3
import psycopg

SQLITE_PATH = "db.sqlite3"
SUPABASE_URL = "postgresql://postgres.sdcqglfvkausnmqrpmsi:Helloworld@2121@hello@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"

TABLES_TO_SYNC = [
    "fms_department",
    "fms_jobposition",
    "fms_employee",
    "fms_employeeprofile",
    "fms_customer",
    "fms_product",
    "fms_productimage",
    "fms_productcolor",
    "fms_productsize",
    "fms_producttextile",
    "fms_productvariant",
    "fms_inventorylog",
    "fms_order",
    "fms_paymenttransaction",
    "auth_user",
]

def sync():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg.connect(
        host="aws-1-ap-northeast-1.pooler.supabase.com",
        port=5432,
        user="postgres.sdcqglfvkausnmqrpmsi",
        password="Helloworld@2121@hello",
        dbname="postgres"
    )
    pg_cur = pg_conn.cursor()

    print("Disabling foreign key checks temporarily for initial load...")
    pg_cur.execute("SET session_replication_role = 'replica';")

    for table in TABLES_TO_SYNC:
        print(f"Syncing {table}...")
        sqlite_cur.execute(f"PRAGMA table_info({table});")
        sqlite_cols = [c[1] for c in sqlite_cur.fetchall()]
        if not sqlite_cols:
            print(f"  Skipping {table} (not found in sqlite)")
            continue

        pg_cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table}';
        """)
        pg_cols = set(c[0] for c in pg_cur.fetchall())
        common_cols = [c for c in sqlite_cols if c in pg_cols]

        sqlite_cur.execute(f"SELECT {', '.join(common_cols)} FROM {table};")
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"  No rows in sqlite for {table}")
            continue

        pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")

        cols_str = ", ".join(common_cols)
        placeholders = ", ".join(["%s"] * len(common_cols))
        insert_query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders});"

        pg_cur.executemany(insert_query, rows)
        print(f"  Inserted {len(rows)} rows into {table}")

        # Update sequence if id or sl exists
        pk_col = "sl" if "sl" in common_cols else ("id" if "id" in common_cols else None)
        if pk_col:
            seq_query = f"""
                SELECT setval(pg_get_serial_sequence('{table}', '{pk_col}'), 
                              COALESCE((SELECT MAX({pk_col}) FROM {table}), 1));
            """
            try:
                pg_cur.execute(seq_query)
            except Exception:
                pass

    pg_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()

    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()
    print("ALL TABLES SYNCED SUCCESSFULLY!")

if __name__ == "__main__":
    sync()
