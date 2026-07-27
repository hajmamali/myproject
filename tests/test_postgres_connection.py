import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres"
    )
    cur = conn.cursor()
    cur.execute("SELECT version();")
    print("PostgreSQL version:", cur.fetchone())
    cur.close()
    conn.close()
    print("Connection successful.")
except Exception as e:
    print("Connection failed:", e)
