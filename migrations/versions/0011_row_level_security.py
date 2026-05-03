"""row level security policies

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-03 00:00:11 UTC

Habilita Row Level Security (RLS) en todas las tablas sensibles y crea
las políticas de acceso multi-tenant.

Principios:
  · Los profesores solo ven sus propios datos (user_id = app.current_user_id)
  · ops.audit_logs: solo INSERT permitido (ni el backend puede borrar el historial)
  · El contexto de usuario se establece con SET app.current_user_id = '...'
    al inicio de cada request en la capa de aplicación.

Nota: Las políticas son PERMISSIVE por defecto (basta con que una sea TRUE).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ops.audit_logs — append-only ──────────────────────────────────────────
    op.execute("ALTER TABLE ops.audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY audit_insert_only ON ops.audit_logs
            FOR INSERT WITH CHECK (TRUE)
    """)

    # ── pedagogy.assignments ──────────────────────────────────────────────────
    op.execute("ALTER TABLE pedagogy.assignments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_owns_assignment ON pedagogy.assignments
            USING (
                user_id = current_setting('app.current_user_id', TRUE)::UUID
            )
    """)

    # ── pedagogy.submissions ──────────────────────────────────────────────────
    op.execute("ALTER TABLE pedagogy.submissions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_owns_submission ON pedagogy.submissions
            USING (
                assignment_id IN (
                    SELECT id FROM pedagogy.assignments
                    WHERE user_id = current_setting('app.current_user_id', TRUE)::UUID
                )
            )
    """)

    # ── pedagogy.grades ───────────────────────────────────────────────────────
    op.execute("ALTER TABLE pedagogy.grades ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY teacher_owns_grade ON pedagogy.grades
            USING (
                assignment_id IN (
                    SELECT id FROM pedagogy.assignments
                    WHERE user_id = current_setting('app.current_user_id', TRUE)::UUID
                )
            )
    """)

    # ── billing.subscriptions ─────────────────────────────────────────────────
    op.execute("ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_owns_subscription ON billing.subscriptions
            USING (
                user_id = current_setting('app.current_user_id', TRUE)::UUID
            )
    """)

    # ── core.api_keys ─────────────────────────────────────────────────────────
    op.execute("ALTER TABLE core.api_keys ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_owns_api_key ON core.api_keys
            USING (
                user_id = current_setting('app.current_user_id', TRUE)::UUID
            )
    """)

    # ── billing.token_wallet ──────────────────────────────────────────────────
    op.execute("ALTER TABLE billing.token_wallet ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_owns_wallet ON billing.token_wallet
            USING (
                user_id = current_setting('app.current_user_id', TRUE)::UUID
            )
    """)

    # ── billing.token_transactions ────────────────────────────────────────────
    op.execute("ALTER TABLE billing.token_transactions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_owns_token_tx ON billing.token_transactions
            USING (
                user_id = current_setting('app.current_user_id', TRUE)::UUID
            )
    """)


def downgrade() -> None:
    # Eliminar políticas y deshabilitar RLS (orden inverso)
    op.execute("DROP POLICY IF EXISTS user_owns_token_tx    ON billing.token_transactions")
    op.execute("ALTER TABLE billing.token_transactions DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS user_owns_wallet       ON billing.token_wallet")
    op.execute("ALTER TABLE billing.token_wallet DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS user_owns_api_key      ON core.api_keys")
    op.execute("ALTER TABLE core.api_keys DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS user_owns_subscription ON billing.subscriptions")
    op.execute("ALTER TABLE billing.subscriptions DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS teacher_owns_grade     ON pedagogy.grades")
    op.execute("ALTER TABLE pedagogy.grades DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS teacher_owns_submission ON pedagogy.submissions")
    op.execute("ALTER TABLE pedagogy.submissions DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS teacher_owns_assignment ON pedagogy.assignments")
    op.execute("ALTER TABLE pedagogy.assignments DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS audit_insert_only      ON ops.audit_logs")
    op.execute("ALTER TABLE ops.audit_logs DISABLE ROW LEVEL SECURITY")
