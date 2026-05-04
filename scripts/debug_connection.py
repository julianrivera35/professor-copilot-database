"""Debug: muestra exactamente a qué BD se conecta Alembic."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

url = os.environ.get("DATABASE_URL")
print(f"DATABASE_URL desde .env: {url}")

import psycopg2
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("SELECT current_database(), current_user")
row = cur.fetchone()
print(f"BD activa: {row[0]}, usuario: {row[1]}")

cur.execute("""
    SELECT table_schema, count(*) 
    FROM information_schema.tables 
    WHERE table_schema IN ('auth','billing','core','pedagogy','ops')
    GROUP BY table_schema
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  Schema '{r[0]}': {r[1]} tablas")
else:
    print("  No hay schemas de la app — la BD está vacía")

# Buscar alembic_version en TODOS los schemas
cur.execute("""
    SELECT schemaname, tablename FROM pg_tables 
    WHERE tablename = 'alembic_version'
""")
rows = cur.fetchall()
print(f"\nalembic_version encontrada en: {rows if rows else 'NINGÚN schema'}")

cur.close()
conn.close()
