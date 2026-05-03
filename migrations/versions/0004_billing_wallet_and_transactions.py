"""billing wallet and token transactions

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-03 00:00:04 UTC

Crea:
  · billing.token_wallet       — saldo real (source of truth) por usuario
  · billing.token_transactions — ledger contable append-only

Nota: token_transactions tiene FK hacia pedagogy.grades (grade_id).
Como pedagogy.grades aún no existe, esa FK se agrega como DEFERRABLE
y la tabla de grades se crea en 0008. Esto es válido porque la FK
solo se resuelve en tiempo de commit de cada transacción, no al crear la tabla.

Alternativa: la FK hacia grades se agrega en 0008 con ALTER TABLE.
Elegimos la segunda opción para mayor claridad.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── billing.token_wallet ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE billing.token_wallet (
            id                     UUID   PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                UUID   NOT NULL
                                              REFERENCES auth.users (id)
                                              ON DELETE RESTRICT,

            -- Dos bolsillos separados
            balance_free           BIGINT NOT NULL DEFAULT 0
                                              CHECK (balance_free >= 0),
            balance_paid           BIGINT NOT NULL DEFAULT 0
                                              CHECK (balance_paid >= 0),

            -- Columna generada: nunca se desincroniza
            balance_total          BIGINT GENERATED ALWAYS AS
                                       (balance_free + balance_paid) STORED,

            -- Acumulados históricos para dashboards
            total_tokens_purchased BIGINT NOT NULL DEFAULT 0,
            total_tokens_consumed  BIGINT NOT NULL DEFAULT 0,

            updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_wallet_user UNIQUE (user_id)
        )
    """)

    op.execute("CREATE INDEX idx_wallet_user ON billing.token_wallet (user_id)")

    op.execute("""
        COMMENT ON TABLE billing.token_wallet IS
            'Saldo de tokens por usuario. balance_free se consume antes que balance_paid.'
    """)
    op.execute("""
        COMMENT ON COLUMN billing.token_wallet.balance_free IS
            'Tokens gratuitos (grant inicial). Se consumen primero.'
    """)
    op.execute("""
        COMMENT ON COLUMN billing.token_wallet.balance_paid IS
            'Tokens comprados por el usuario. Se consumen tras agotar balance_free.'
    """)
    op.execute("""
        COMMENT ON COLUMN billing.token_wallet.balance_total IS
            'Columna GENERATED: balance_free + balance_paid. No editar.'
    """)

    # ── billing.token_transactions ────────────────────────────────────────────
    # grade_id FK se agrega en 0008 una vez que pedagogy.grades existe.
    op.execute("""
        CREATE TABLE billing.token_transactions (
            id                  UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID          NOT NULL
                                                  REFERENCES auth.users (id)
                                                  ON DELETE RESTRICT,
            wallet_id           UUID          NOT NULL
                                                  REFERENCES billing.token_wallet (id)
                                                  ON DELETE RESTRICT,

            -- Tipo y origen del movimiento
            tx_type             token_tx_type NOT NULL,
            token_source        token_source,

            -- Montos (positivo = crédito, negativo = débito)
            tokens_free_delta   BIGINT        NOT NULL DEFAULT 0,
            tokens_paid_delta   BIGINT        NOT NULL DEFAULT 0,

            -- Snapshot del saldo resultante
            balance_free_after  BIGINT        NOT NULL,
            balance_paid_after  BIGINT        NOT NULL,

            -- Referencias de trazabilidad (grade_id FK se añade en 0008)
            grade_id            UUID,
            package_id          UUID          REFERENCES billing.token_packages (id)
                                                  ON DELETE SET NULL,
            external_payment_id TEXT,

            -- Costo real (solo en consumptions)
            ai_cost_cents       NUMERIC(10, 4),

            description         TEXT,
            created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX idx_token_tx_user
            ON billing.token_transactions (user_id, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX idx_token_tx_grade
            ON billing.token_transactions (grade_id)
            WHERE grade_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX idx_token_tx_type
            ON billing.token_transactions (tx_type, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE billing.token_transactions IS
            'Ledger append-only de todos los movimientos de tokens. Fuente de verdad financiera.'
    """)
    op.execute("""
        COMMENT ON COLUMN billing.token_transactions.tokens_free_delta IS
            'Positivo = crédito, negativo = débito sobre balance_free.'
    """)
    op.execute("""
        COMMENT ON COLUMN billing.token_transactions.tokens_paid_delta IS
            'Positivo = crédito, negativo = débito sobre balance_paid.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing.token_transactions")
    op.execute("DROP TABLE IF EXISTS billing.token_wallet")
