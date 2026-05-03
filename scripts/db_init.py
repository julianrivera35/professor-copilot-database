"""
scripts/db_init.py
==================
Inicializa la base de datos desde cero y aplica todas las migraciones.

Uso:
    python scripts/db_init.py
    python -m scripts.db_init
    db-migrate              # si está instalado como entrypoint

El script:
  1. Verifica que DATABASE_URL esté configurado
  2. Crea la base de datos si no existe (conectando a 'postgres')
  3. Corre `alembic upgrade head`
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# ── Raíz del proyecto ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print(
            "ERROR: La variable de entorno DATABASE_URL no está configurada.\n"
            "  Copia .env.example a .env y rellena los valores.",
            file=sys.stderr,
        )
        sys.exit(1)
    return url


def create_database_if_not_exists(database_url: str) -> None:
    """
    Intenta crear la base de datos apuntando al servidor con la BD 'postgres'.
    Si la BD ya existe, ignora el error.
    """
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print(
            "WARNING: psycopg2 no disponible para crear la BD automáticamente.\n"
            "  Asegúrate de que la BD exista antes de correr las migraciones.",
            file=sys.stderr,
        )
        return

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")

    # Conectar al servidor sin especificar BD (usando 'postgres')
    server_url = urlunparse(parsed._replace(path="/postgres"))

    try:
        conn = psycopg2.connect(server_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✓ Base de datos '{db_name}' creada.")
        else:
            print(f"✓ Base de datos '{db_name}' ya existe.")

        cur.close()
        conn.close()
    except Exception as exc:
        print(f"WARNING: No se pudo crear la BD automáticamente: {exc}", file=sys.stderr)
        print("  Asegúrate de que la BD exista antes de continuar.", file=sys.stderr)


def run_migrations() -> None:
    """Ejecuta alembic upgrade head desde la raíz del proyecto."""
    print("\n▶ Aplicando migraciones...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=ROOT,
        capture_output=False,
    )
    if result.returncode != 0:
        print("\nERROR: Las migraciones fallaron.", file=sys.stderr)
        sys.exit(result.returncode)
    print("\n✓ Todas las migraciones aplicadas exitosamente.")


def main() -> None:
    print("═══════════════════════════════════════")
    print("  Professor Copilot — DB Init")
    print("═══════════════════════════════════════\n")

    database_url = get_database_url()
    print(f"  BD: {database_url.split('@')[-1]}")  # Ocultar credenciales en el log

    create_database_if_not_exists(database_url)
    run_migrations()


if __name__ == "__main__":
    main()
