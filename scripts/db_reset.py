"""
scripts/db_reset.py
===================
Destruye y recrea la base de datos completa. USO EXCLUSIVO EN DESARROLLO.

Uso:
    python scripts/db_reset.py
    python -m scripts.db_reset
    db-reset                    # si está instalado como entrypoint

El script:
  1. Pide confirmación explícita (a menos que se pase --yes)
  2. Baja todas las migraciones hasta base (alembic downgrade base)
  3. Sube de nuevo a head (alembic upgrade head)

Para un reset destructivo total (DROP + CREATE de BD), pasa --hard.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Protección: nunca correr en producción
_SAFE_ENV_VALUES = {"development", "dev", "local", "test", ""}


def check_environment() -> None:
    app_env = os.environ.get("APP_ENV", "").lower()
    if app_env not in _SAFE_ENV_VALUES:
        print(
            f"ERROR: db_reset NO está permitido en entorno '{app_env}'.\n"
            "  Este script es solo para desarrollo local.",
            file=sys.stderr,
        )
        sys.exit(1)


def confirm(yes: bool = False) -> None:
    if yes:
        return
    print("⚠️  ADVERTENCIA: Esto borrará y recreará toda la base de datos.")
    answer = input("  ¿Estás seguro? Escribe 'RESET' para confirmar: ")
    if answer.strip() != "RESET":
        print("Operación cancelada.")
        sys.exit(0)


def hard_reset(database_url: str) -> None:
    """Drop y recreación completa de la BD."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("ERROR: psycopg2 requerido para --hard.", file=sys.stderr)
        sys.exit(1)

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")
    server_url = urlunparse(parsed._replace(path="/postgres"))

    conn = psycopg2.connect(server_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Terminar conexiones activas antes de drop
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
    """, (db_name,))
    cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    cur.execute(f'CREATE DATABASE "{db_name}"')
    print(f"✓ Base de datos '{db_name}' recreada desde cero.")

    cur.close()
    conn.close()


def alembic(cmd: list[str]) -> None:
    result = subprocess.run(["alembic"] + cmd, cwd=ROOT, capture_output=False)
    if result.returncode != 0:
        print(f"\nERROR: alembic {' '.join(cmd)} falló.", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    check_environment()

    yes = "--yes" in sys.argv or "-y" in sys.argv
    hard = "--hard" in sys.argv

    print("═══════════════════════════════════════")
    print("  Professor Copilot — DB Reset")
    print("  ⚠️  Solo para desarrollo local")
    print("═══════════════════════════════════════\n")

    confirm(yes=yes)

    database_url = os.environ.get("DATABASE_URL", "")

    if hard:
        print("\n▶ Hard reset: eliminando y recreando la BD...")
        hard_reset(database_url)
        print("\n▶ Aplicando migraciones desde cero...")
        alembic(["upgrade", "head"])
    else:
        print("\n▶ Bajando todas las migraciones...")
        alembic(["downgrade", "base"])
        print("\n▶ Aplicando todas las migraciones...")
        alembic(["upgrade", "head"])

    print("\n✓ Reset completado.")


if __name__ == "__main__":
    main()
