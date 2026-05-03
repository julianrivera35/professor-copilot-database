"""billing subscriptions and usage quotas

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03 00:00:05 UTC

Crea:
  · billing.subscriptions — vincula usuario con plan y proveedor de pago externo
  · billing.usage_quotas  — contadores mensuales de referencia para el panel admin
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── billing.subscriptions ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE billing.subscriptions (
            id                   UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id              UUID              NOT NULL
                                                      REFERENCES auth.users (id)
                                                      ON DELETE RESTRICT,
            plan_id              UUID              NOT NULL
                                                      REFERENCES billing.plans (id)
                                                      ON DELETE RESTRICT,

            status               sub_status        NOT NULL DEFAULT 'trialing',
            billing_cycle        plan_billing_cycle NOT NULL DEFAULT 'monthly',

            -- Integración con proveedor externo
            payment_provider     payment_provider  NOT NULL DEFAULT 'stripe',
            external_sub_id      TEXT,
            external_customer_id TEXT,

            -- Períodos de facturación
            current_period_start TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            current_period_end   TIMESTAMPTZ       NOT NULL,

            -- Cancelación
            cancel_at            TIMESTAMPTZ,
            canceled_at          TIMESTAMPTZ,

            -- Trial
            trial_ends_at        TIMESTAMPTZ,

            -- Metadatos de pago para auditoría interna
            metadata             JSONB             NOT NULL DEFAULT '{}',

            created_at           TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ       NOT NULL DEFAULT NOW()
        )
    """)

    # Un usuario solo puede tener una suscripción activa simultánea
    op.execute("""
        CREATE UNIQUE INDEX uq_subscriptions_user_active
            ON billing.subscriptions (user_id)
            WHERE status IN ('trialing', 'active', 'past_due')
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_subscriptions_external
            ON billing.subscriptions (payment_provider, external_sub_id)
            WHERE external_sub_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX idx_subscriptions_status
            ON billing.subscriptions (status, current_period_end)
    """)

    op.execute("""
        COMMENT ON TABLE billing.subscriptions IS
            'Suscripción activa por usuario. Una sola activa simultánea.'
    """)

    # ── billing.usage_quotas ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE billing.usage_quotas (
            id              UUID     PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         UUID     NOT NULL
                                         REFERENCES auth.users (id)
                                         ON DELETE CASCADE,
            subscription_id UUID     NOT NULL
                                         REFERENCES billing.subscriptions (id)
                                         ON DELETE CASCADE,

            -- Clave de período
            period_year     SMALLINT NOT NULL,
            period_month    SMALLINT NOT NULL
                                         CHECK (period_month BETWEEN 1 AND 12),

            -- Contadores acumulados en el período
            assignments_used   INTEGER NOT NULL DEFAULT 0,
            students_processed INTEGER NOT NULL DEFAULT 0,
            tokens_consumed    BIGINT  NOT NULL DEFAULT 0,
            files_uploaded_mb  INTEGER NOT NULL DEFAULT 0,

            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_quota_user_period
                UNIQUE (user_id, period_year, period_month)
        )
    """)

    op.execute("""
        CREATE INDEX idx_quotas_user_period
            ON billing.usage_quotas (user_id, period_year, period_month)
    """)

    op.execute("""
        COMMENT ON TABLE billing.usage_quotas IS
            'Contadores mensuales de referencia. El límite real es el saldo del wallet.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing.usage_quotas")
    op.execute("DROP TABLE IF EXISTS billing.subscriptions")
