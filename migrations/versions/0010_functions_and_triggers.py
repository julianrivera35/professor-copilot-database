"""functions and triggers

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-03 00:00:10 UTC

Crea las funciones PL/pgSQL y triggers del sistema:

  1. set_updated_at()                  → mantiene updated_at sincronizado
  2. create_wallet_on_signup()         → crea wallet con saldo 0 al registrar usuario
  3. grant_initial_tokens()            → acredita tokens del plan al activar suscripción
  4. deduct_tokens_on_grade()          → descuenta wallet al completar una calificación
                                         (solo si token_source = 'platform')

El trigger de set_updated_at se aplica a todas las tablas que tienen
la columna updated_at usando un bloque DO dinámico.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Función set_updated_at ─────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$
    """)

    # Aplicar a todas las tablas con updated_at en nuestros schemas
    op.execute("""
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT table_schema, table_name
                FROM information_schema.columns
                WHERE column_name = 'updated_at'
                  AND table_schema IN ('auth', 'billing', 'core', 'pedagogy', 'ops')
            LOOP
                EXECUTE format(
                    'CREATE TRIGGER trg_updated_at
                     BEFORE UPDATE ON %I.%I
                     FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
                    t.table_schema, t.table_name
                );
            END LOOP;
        END;
        $$
    """)

    # ── 2. Función create_wallet_on_signup ────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION create_wallet_on_signup()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO billing.token_wallet (user_id, balance_free)
            VALUES (NEW.id, 0);
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        CREATE TRIGGER trg_wallet_on_signup
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION create_wallet_on_signup()
    """)

    # ── 3. Función grant_initial_tokens ───────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION grant_initial_tokens()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            v_grant       BIGINT;
            v_wallet      UUID;
            v_free_before BIGINT;
        BEGIN
            -- Solo al pasar a 'active' o 'trialing' por primera vez
            IF NEW.status IN ('active', 'trialing') AND
               OLD.status IS DISTINCT FROM NEW.status THEN

                -- Leer tokens iniciales del plan
                SELECT COALESCE((p.features->>'initial_grant_tokens')::BIGINT, 0)
                INTO v_grant
                FROM billing.plans p WHERE p.id = NEW.plan_id;

                IF v_grant > 0 THEN
                    SELECT id, balance_free
                    INTO v_wallet, v_free_before
                    FROM billing.token_wallet WHERE user_id = NEW.user_id;

                    UPDATE billing.token_wallet
                    SET balance_free = balance_free + v_grant,
                        updated_at   = NOW()
                    WHERE user_id = NEW.user_id;

                    INSERT INTO billing.token_transactions (
                        user_id, wallet_id, tx_type,
                        tokens_free_delta, balance_free_after, balance_paid_after,
                        description
                    )
                    SELECT
                        NEW.user_id, v_wallet, 'initial_grant',
                        v_grant, v_free_before + v_grant, balance_paid,
                        'Tokens iniciales por activación de plan'
                    FROM billing.token_wallet WHERE user_id = NEW.user_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        CREATE TRIGGER trg_grant_tokens_on_subscription
        AFTER UPDATE OF status ON billing.subscriptions
        FOR EACH ROW EXECUTE FUNCTION grant_initial_tokens()
    """)

    # ── 4. Función deduct_tokens_on_grade ─────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION deduct_tokens_on_grade()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            v_user_id     UUID;
            v_wallet      billing.token_wallet%ROWTYPE;
            v_total_tok   BIGINT;
            v_free_deduct BIGINT;
            v_paid_deduct BIGINT;
        BEGIN
            -- Solo en INSERT de grades con token_source = 'platform'
            IF NEW.token_source = 'own_key' THEN
                RETURN NEW;
            END IF;

            v_total_tok := COALESCE(NEW.tokens_input, 0) + COALESCE(NEW.tokens_output, 0);
            IF v_total_tok = 0 THEN RETURN NEW; END IF;

            -- Obtener user_id desde el assignment
            SELECT a.user_id INTO v_user_id
            FROM pedagogy.assignments a WHERE a.id = NEW.assignment_id;

            SELECT * INTO v_wallet
            FROM billing.token_wallet WHERE user_id = v_user_id FOR UPDATE;

            IF NOT FOUND THEN RETURN NEW; END IF;

            -- Consumir primero gratuitos, luego pagados
            v_free_deduct := LEAST(v_total_tok, v_wallet.balance_free);
            v_paid_deduct := LEAST(v_total_tok - v_free_deduct, v_wallet.balance_paid);

            UPDATE billing.token_wallet
            SET balance_free          = balance_free  - v_free_deduct,
                balance_paid          = balance_paid  - v_paid_deduct,
                total_tokens_consumed = total_tokens_consumed + v_total_tok,
                updated_at            = NOW()
            WHERE user_id = v_user_id;

            INSERT INTO billing.token_transactions (
                user_id, wallet_id, tx_type, token_source,
                tokens_free_delta, tokens_paid_delta,
                balance_free_after, balance_paid_after,
                grade_id, ai_cost_cents, description
            ) VALUES (
                v_user_id, v_wallet.id, 'consumption', 'platform',
                -v_free_deduct, -v_paid_deduct,
                v_wallet.balance_free  - v_free_deduct,
                v_wallet.balance_paid  - v_paid_deduct,
                NEW.id, NEW.ai_cost_cents,
                'Calificación IA: ' || v_total_tok || ' tokens'
            );

            -- Actualizar quota mensual de referencia
            INSERT INTO billing.usage_quotas
                (user_id, subscription_id, period_year, period_month,
                 students_processed, tokens_consumed)
            SELECT
                v_user_id, s.id,
                EXTRACT(YEAR  FROM NOW())::SMALLINT,
                EXTRACT(MONTH FROM NOW())::SMALLINT,
                1, v_total_tok
            FROM billing.subscriptions s
            WHERE s.user_id = v_user_id
              AND s.status IN ('active', 'trialing')
            LIMIT 1
            ON CONFLICT (user_id, period_year, period_month)
            DO UPDATE SET
                students_processed = billing.usage_quotas.students_processed + 1,
                tokens_consumed    = billing.usage_quotas.tokens_consumed + v_total_tok,
                updated_at         = NOW();

            RETURN NEW;
        END;
        $$
    """)

    op.execute("""
        CREATE TRIGGER trg_deduct_tokens_on_grade
        AFTER INSERT ON pedagogy.grades
        FOR EACH ROW EXECUTE FUNCTION deduct_tokens_on_grade()
    """)


def downgrade() -> None:
    # Quitar triggers antes que las funciones
    op.execute("DROP TRIGGER IF EXISTS trg_deduct_tokens_on_grade ON pedagogy.grades")
    op.execute("DROP TRIGGER IF EXISTS trg_grant_tokens_on_subscription ON billing.subscriptions")
    op.execute("DROP TRIGGER IF EXISTS trg_wallet_on_signup ON auth.users")

    # Quitar triggers de updated_at en todas las tablas
    op.execute("""
        DO $$
        DECLARE
            t RECORD;
        BEGIN
            FOR t IN
                SELECT table_schema, table_name
                FROM information_schema.columns
                WHERE column_name = 'updated_at'
                  AND table_schema IN ('auth', 'billing', 'core', 'pedagogy', 'ops')
            LOOP
                EXECUTE format(
                    'DROP TRIGGER IF EXISTS trg_updated_at ON %I.%I',
                    t.table_schema, t.table_name
                );
            END LOOP;
        END;
        $$
    """)

    op.execute("DROP FUNCTION IF EXISTS deduct_tokens_on_grade()")
    op.execute("DROP FUNCTION IF EXISTS grant_initial_tokens()")
    op.execute("DROP FUNCTION IF EXISTS create_wallet_on_signup()")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
