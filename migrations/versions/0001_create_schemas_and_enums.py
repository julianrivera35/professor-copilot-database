"""create schemas and enums

Revision ID: 0001
Revises:
Create Date: 2026-05-03 00:00:01 UTC

Crea las extensiones PostgreSQL, los schemas de la aplicación
y todos los tipos ENUM. Va primero porque todo lo demás depende de ellos.

Nota sobre downgrade de ENUMs:
  PostgreSQL no permite DROP TYPE si hay columnas activas que usan ese tipo.
  El downgrade completo solo es seguro tras eliminar todas las tablas primero
  (lo que hace 0002 en su downgrade). Por tanto aquí el downgrade solo borra
  schemas; los ENUMs se eliminan en cascada con las tablas en migraciones posteriores.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensiones ───────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gin"')

    # ── Schemas ───────────────────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute("CREATE SCHEMA IF NOT EXISTS billing")
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS pedagogy")
    op.execute("CREATE SCHEMA IF NOT EXISTS ops")

    # ── ENUMs — auth ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE user_role AS ENUM (
            'teacher', 'admin', 'superadmin'
        )
    """)
    op.execute("""
        CREATE TYPE user_status AS ENUM (
            'active', 'suspended', 'pending_verification', 'deleted'
        )
    """)

    # ── ENUMs — billing ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE plan_billing_cycle AS ENUM ('monthly', 'annual')
    """)
    op.execute("""
        CREATE TYPE sub_status AS ENUM (
            'trialing', 'active', 'past_due', 'canceled', 'paused'
        )
    """)
    op.execute("""
        CREATE TYPE payment_provider AS ENUM ('stripe', 'paypal', 'manual')
    """)
    op.execute("""
        CREATE TYPE token_tx_type AS ENUM (
            'initial_grant',
            'purchase',
            'consumption',
            'refund',
            'adjustment'
        )
    """)
    op.execute("""
        CREATE TYPE token_source AS ENUM ('platform', 'own_key')
    """)

    # ── ENUMs — core ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE ai_provider AS ENUM (
            'openai', 'anthropic', 'google', 'custom'
        )
    """)

    # ── ENUMs — pedagogy ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE assignment_status AS ENUM (
            'draft', 'active', 'grading', 'completed', 'archived'
        )
    """)
    op.execute("""
        CREATE TYPE extraction_status AS ENUM (
            'pending', 'processing', 'completed', 'failed'
        )
    """)
    op.execute("""
        CREATE TYPE processing_status AS ENUM (
            'pending', 'queued', 'processing', 'completed', 'failed', 'skipped'
        )
    """)

    # ── ENUMs — ops ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE export_format AS ENUM ('csv', 'xlsx')
    """)
    op.execute("""
        CREATE TYPE export_status AS ENUM (
            'pending', 'processing', 'completed', 'failed', 'expired'
        )
    """)


def downgrade() -> None:
    # Los ENUMs solo se pueden borrar luego de que no haya tablas usándolos.
    # Las tablas se borran en sus propias migraciones (0002-0009).
    # Aquí solo eliminamos los schemas vacíos.
    op.execute("DROP SCHEMA IF EXISTS ops CASCADE")
    op.execute("DROP SCHEMA IF EXISTS pedagogy CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
    op.execute("DROP SCHEMA IF EXISTS billing CASCADE")
    op.execute("DROP SCHEMA IF EXISTS auth CASCADE")

    # ENUMs (seguro aquí porque los schemas ya están caídos)
    op.execute("DROP TYPE IF EXISTS export_status")
    op.execute("DROP TYPE IF EXISTS export_format")
    op.execute("DROP TYPE IF EXISTS processing_status")
    op.execute("DROP TYPE IF EXISTS extraction_status")
    op.execute("DROP TYPE IF EXISTS assignment_status")
    op.execute("DROP TYPE IF EXISTS ai_provider")
    op.execute("DROP TYPE IF EXISTS token_source")
    op.execute("DROP TYPE IF EXISTS token_tx_type")
    op.execute("DROP TYPE IF EXISTS payment_provider")
    op.execute("DROP TYPE IF EXISTS sub_status")
    op.execute("DROP TYPE IF EXISTS plan_billing_cycle")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_role")
