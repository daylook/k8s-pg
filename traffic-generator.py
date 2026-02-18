import time
import psycopg2
from datetime import datetime

# === CONFIGURE THESE ===
HOST = "127.0.0.1"     # explicit IPv4 to avoid IPv6 issues with port-forward
PORT = 5432
USER = "postgres"
# PASSWORD will be injected via env or replaced below
DBNAME = "postgres"
TABLE = "traffic_log"

def main(password):
    conn_params = {
        "host": HOST,
        "port": PORT,
        "user": USER,
        "password": password,
        "dbname": DBNAME,
        "sslmode": "require",
    }
    print("🚀 Traffic generator started - writing every 100ms")
    conn = None
    while True:
        try:
            if conn is None or conn.closed:
                conn = psycopg2.connect(**conn_params, connect_timeout=2)
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {TABLE} (ts) VALUES (NOW())
                    ON CONFLICT DO NOTHING;
                """)
                conn.commit()
            print(f"✅ [{datetime.now().isoformat()}] Write succeeded")
        except psycopg2.OperationalError as e:
            msg = str(e).strip().replace("\n", " ")
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            if "Connection refused" in msg:
                print(f"❌ [{datetime.now().isoformat()}] Connection refused — is port-forward running? Start it with: PRIMARY=$(kubectl get cluster ha-postgres -o jsonpath='{{.status.currentPrimary}}') && kubectl port-forward pod/$PRIMARY 5432:5432")
            else:
                print(f"❌ [{datetime.now().isoformat()}] Transient error (expected during switchover): {msg}")
        except Exception as e:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            print(f"❌ [{datetime.now().isoformat()}] Unexpected error: {e}")
        time.sleep(0.1)

if __name__ == "__main__":
    import os
    pwd = os.getenv("PGPASSWORD") or input("Enter postgres superuser password: ")
    main(pwd)
