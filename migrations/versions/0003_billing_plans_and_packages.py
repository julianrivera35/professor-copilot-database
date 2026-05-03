"""billing plans and token packages

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03 00:00:03 UTC

Crea las tablas de catálogo de billing que no tienen FK hacia otras tablas de billing:
  · billing.plans         — catálogo de planes (features + grant inicial)
  · billing.token_packages — menú de packs de tokens a la venta

Los seeds se insertan en la migración 0013 para mantener el schema separado de los datos.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── billing.plans ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE billing.plans (
            id                          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            name                        TEXT    NOT NULL,
            slug                        TEXT    NOT NULL,

            -- Precios en centavos (evita decimales flotantes)
            monthly_price_cents         INTEGER NOT NULL DEFAULT 0,
            annual_price_cents          INTEGER NOT NULL DEFAULT 0,
            currency                    CHAR(3) NOT NULL DEFAULT 'USD',

            -- Límites del plan (legacy: el límite real es el wallet)
            max_assignments_per_month   INTEGER NOT NULL DEFAULT 5,
            max_students_per_assignment INTEGER NOT NULL DEFAULT 30,
            max_file_size_mb            INTEGER NOT NULL DEFAULT 10,

            -- Feature flags
            allow_api_access            BOOLEAN NOT NULL DEFAULT FALSE,
            allow_custom_rubrics        BOOLEAN NOT NULL DEFAULT TRUE,
            allow_bulk_upload           BOOLEAN NOT NULL DEFAULT FALSE,
            allow_export                BOOLEAN NOT NULL DEFAULT TRUE,

            -- Flags adicionales extensibles sin migración
            -- Contiene: initial_grant_tokens, allow_own_api_key
            features                    JSONB   NOT NULL DEFAULT '{}',

            is_active                   BOOLEAN  NOT NULL DEFAULT TRUE,
            sort_order                  SMALLINT NOT NULL DEFAULT 0,

            created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE UNIQUE INDEX uq_plans_slug ON billing.plans (slug)")

    op.execute("""
        COMMENT ON TABLE billing.plans IS
            'Catálogo de planes. Controla features y grant inicial de tokens, no cuotas duras.'
    """)

    # ── billing.token_packages ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE billing.token_packages (
            id           UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
            name         TEXT     NOT NULL,
            slug         TEXT     NOT NULL,
            token_amount BIGINT   NOT NULL,
            price_cents  INTEGER  NOT NULL,
            currency     CHAR(3)  NOT NULL DEFAULT 'USD',
            bonus_tokens BIGINT   NOT NULL DEFAULT 0,
            is_active    BOOLEAN  NOT NULL DEFAULT TRUE,
            sort_order   SMALLINT NOT NULL DEFAULT 0,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_token_packages_slug
            ON billing.token_packages (slug)
    """)

    op.execute("""
        COMMENT ON TABLE billing.token_packages IS
            'Paquetes de tokens disponibles para compra. Independiente del plan.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing.token_packages")
    op.execute("DROP TABLE IF EXISTS billing.plans")
