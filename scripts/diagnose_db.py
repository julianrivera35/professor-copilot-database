"""Diagnóstico de conexión y búsqueda de la BD correcta."""
import os
from dotenv import load_dotenv
load_dotenv(".env")

import psycopg2

url = os.environ["DATABASE_URL"]
print(f"DATABASE_URL: {url}\n")

conn = psycopg2.connect(url)
cur = conn.cursor()

cur.execute("SELECT current_database(), current_user, version()")
row = cur.fetchone()
print(f"Base de datos activa : {row[0]}")
print(f"Usuario conectado    : {row[1]}")
print(f"PostgreSQL version   : {row[2][:40]}...\n")

cur.execute("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
print("Schemas disponibles:")
for r in cur.fetchall():
    print(f"  {r[0]}")

cur.execute("""
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
""")
public_tables = cur.fetchall()
print(f"\nTablas en schema 'public': {[r[0] for r in public_tables]}")

cur.close()
conn.close()
