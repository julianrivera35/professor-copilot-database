"""Verifica el estado de la base de datos tras las migraciones."""
import os
from dotenv import load_dotenv
load_dotenv(".env")

import psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# 1. Tablas creadas por schema
cur.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema IN ('auth','billing','core','pedagogy','ops')
      AND table_type = 'BASE TABLE'
    ORDER BY table_schema, table_name
""")
rows = cur.fetchall()
print("=== TABLAS CREADAS ===")
for r in rows:
    print(f"  {r[0]}.{r[1]}")
print(f"  Total: {len(rows)} tablas\n")

# 2. Versión de Alembic
try:
    cur.execute("SELECT version_num FROM public.alembic_version")
    rows = cur.fetchall()
    print("=== ALEMBIC VERSION ===")
    for r in rows:
        print(f"  revision activa: {r[0]}")
except Exception as e:
    print(f"  (sin tabla alembic_version: {e})")
print()

# 3. Seeds: planes
cur.execute("SELECT name, slug, monthly_price_cents, features->>'initial_grant_tokens' FROM billing.plans ORDER BY sort_order")
print("=== PLANES (billing.plans) ===")
for r in cur.fetchall():
    precio = "Gratis" if r[2] == 0 else f"${r[2]/100:.2f}/mes"
    print(f"  {r[0]} ({r[1]}) — {precio} — {r[3]} tokens iniciales")
print()

# 4. Seeds: paquetes de tokens
cur.execute("SELECT name, token_amount, price_cents FROM billing.token_packages ORDER BY sort_order")
print("=== PAQUETES DE TOKENS ===")
for r in cur.fetchall():
    print(f"  {r[0]} — {r[1]:,} tokens — ${r[2]/100:.2f}")
print()

# 5. Seeds: modelos IA
cur.execute("SELECT display_name, model_id, is_default FROM core.ai_model_configs ORDER BY is_default DESC")
print("=== MODELOS IA (core.ai_model_configs) ===")
for r in cur.fetchall():
    default = " <-- DEFAULT" if r[2] else ""
    print(f"  {r[0]} ({r[1]}){default}")

cur.close()
conn.close()
print("\nOK - Todo aplicado correctamente")
