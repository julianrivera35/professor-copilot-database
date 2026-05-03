"""seeds: initial data

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-03 00:00:13 UTC

Inserta los datos iniciales de catálogo:
  · billing.plans          — Free (50k tokens), Pro (200k), School (500k)
  · billing.token_packages — Starter, Growth, Bulk
  · core.ai_model_configs  — GPT-4o mini (default), Claude Haiku 4.5, Claude Sonnet 4.6

Estos datos se pueden revertir en downgrade sin afectar el schema.

Convención de precios:
  · Todos los precios en centavos de USD (evita problemas de coma flotante)
  · cost_per_1k_input / cost_per_1k_output en USD decimal (para reporting de márgenes)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── billing.plans ─────────────────────────────────────────────────────────
    # max_assignments_per_month y max_students_per_assignment en 999
    # porque el límite real es el saldo del wallet, no cuotas duras.
    op.execute("""
        INSERT INTO billing.plans (
            name, slug,
            monthly_price_cents, annual_price_cents,
            max_assignments_per_month, max_students_per_assignment, max_file_size_mb,
            allow_api_access, allow_bulk_upload,
            sort_order, features
        ) VALUES
            (
                'Free', 'free',
                0, 0,
                999, 999, 10,
                FALSE, FALSE,
                0,
                '{"initial_grant_tokens": 50000, "allow_own_api_key": false}'
            ),
            (
                'Pro', 'pro',
                1900, 19000,
                999, 999, 25,
                FALSE, TRUE,
                1,
                '{"initial_grant_tokens": 200000, "allow_own_api_key": true}'
            ),
            (
                'School', 'school',
                7900, 79000,
                999, 999, 50,
                TRUE, TRUE,
                2,
                '{"initial_grant_tokens": 500000, "allow_own_api_key": true}'
            )
        ON CONFLICT (slug) DO NOTHING
    """)

    # ── billing.token_packages ────────────────────────────────────────────────
    op.execute("""
        INSERT INTO billing.token_packages (
            name, slug, token_amount, price_cents, bonus_tokens, sort_order
        ) VALUES
            ('Starter', 'starter', 100000,   499,       0, 0),
            ('Growth',  'growth',  500000,  1999,   50000, 1),
            ('Bulk',    'bulk',   1500000,  4999,  300000, 2)
        ON CONFLICT (slug) DO NOTHING
    """)

    # ── core.ai_model_configs ─────────────────────────────────────────────────
    op.execute("""
        INSERT INTO core.ai_model_configs (
            provider, model_id, display_name, max_context_tokens,
            cost_per_1k_input, cost_per_1k_output,
            is_active, is_default
        ) VALUES
            (
                'openai', 'gpt-4o-mini', 'GPT-4o mini', 128000,
                0.000150, 0.000600,
                TRUE, TRUE
            ),
            (
                'anthropic', 'claude-haiku-4-5-20251001', 'Claude Haiku 4.5', 200000,
                0.000800, 0.004000,
                TRUE, FALSE
            ),
            (
                'anthropic', 'claude-sonnet-4-6', 'Claude Sonnet 4.6', 200000,
                0.003000, 0.015000,
                TRUE, FALSE
            )
        ON CONFLICT (provider, model_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM core.ai_model_configs
        WHERE model_id IN ('gpt-4o-mini', 'claude-haiku-4-5-20251001', 'claude-sonnet-4-6')
    """)
    op.execute("""
        DELETE FROM billing.token_packages
        WHERE slug IN ('starter', 'growth', 'bulk')
    """)
    op.execute("""
        DELETE FROM billing.plans
        WHERE slug IN ('free', 'pro', 'school')
    """)
