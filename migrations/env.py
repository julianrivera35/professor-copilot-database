"""
migrations/env.py — Entorno de ejecución de Alembic
Professor Copilot Database

Soporta:
  · Modo online  (alembic upgrade head)
  · Modo offline (alembic upgrade head --sql → genera SQL puro)
  · Carga DATABASE_URL desde .env automáticamente
  · Schemas no-public (auth, billing, core, pedagogy, ops)
"""
from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool, text

# ── Cargar .env desde la raíz del proyecto ────────────────────────────────────
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")

# ── Config de Alembic ─────────────────────────────────────────────────────────
config = context.config

# Inyectar DATABASE_URL desde variable de entorno (sobreescribe alembic.ini)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "La variable de entorno DATABASE_URL no está configurada. "
        "Copia .env.example a .env y rellena los valores."
    )
config.set_main_option("sqlalchemy.url", database_url)

# ── Logging ───────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sin target_metadata — migraciones SQL puro (no autogenerate)
target_metadata = None

# Schemas de la aplicación (para include_schemas)
APP_SCHEMAS = ("auth", "billing", "core", "pedagogy", "ops")


def include_name(name, type_, parent_names):
    """Filtro para que Alembic solo examine los schemas del proyecto."""
    if type_ == "schema":
        return name in APP_SCHEMAS
    return True


# ── Modo OFFLINE ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Genera SQL puro sin conectarse a la BD.
    Útil para auditar los cambios antes de aplicarlos en producción.

    Uso:
        alembic upgrade head --sql > upgrade.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=include_name,
        # Comparar tipos de servidor para mayor precisión en diffs
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Modo ONLINE ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Conecta a la BD y aplica las migraciones directamente.

    Se usa NullPool para evitar que las conexiones queden abiertas
    tras terminar (importante en scripts CI/CD y lambdas).
    """
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Asegurarse de que el search_path incluye los schemas necesarios
        connection.execute(
            text("SET search_path TO auth, billing, core, pedagogy, ops, public")
        )
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_name=include_name,
            compare_type=True,
            # Tabla de versiones en schema público para simplicidad
            version_table="alembic_version",
            version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
