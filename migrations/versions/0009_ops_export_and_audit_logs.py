"""ops export logs and audit logs

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-03 00:00:09 UTC

Crea:
  · ops.export_logs — registro de exportaciones CSV/XLSX con expiración a 24h
  · ops.audit_logs  — log de seguridad append-only (RLS: solo INSERT permitido)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ops.export_logs ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ops.export_logs (
            id            UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID          NOT NULL
                                            REFERENCES auth.users (id)
                                            ON DELETE SET NULL,
            assignment_id UUID          REFERENCES pedagogy.assignments (id)
                                            ON DELETE SET NULL,

            format        export_format NOT NULL DEFAULT 'csv',
            status        export_status NOT NULL DEFAULT 'pending',

            storage_path  TEXT,
            row_count     INTEGER,
            error_message TEXT,

            -- El archivo expira y se borra del storage
            expires_at    TIMESTAMPTZ   NOT NULL
                              DEFAULT NOW() + INTERVAL '24 hours',

            created_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX idx_exports_user
            ON ops.export_logs (user_id, created_at DESC)
    """)
    # Índice parcial para el job de limpieza
    op.execute("""
        CREATE INDEX idx_exports_cleanup
            ON ops.export_logs (expires_at)
            WHERE status = 'completed'
    """)

    op.execute("""
        COMMENT ON TABLE ops.export_logs IS
            'Registro de exportaciones CSV/XLSX. Los archivos expiran en 24h.'
    """)

    # ── ops.audit_logs ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE ops.audit_logs (
            id            UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id       UUID  REFERENCES auth.users (id)
                                    ON DELETE SET NULL,

            action        TEXT  NOT NULL,
            resource_type TEXT,
            resource_id   UUID,

            old_values    JSONB,
            new_values    JSONB,

            ip_address    INET,
            user_agent    TEXT,

            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX idx_audit_user_action
            ON ops.audit_logs (user_id, action, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX idx_audit_resource
            ON ops.audit_logs (resource_type, resource_id, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE ops.audit_logs IS
            'Log de auditoría append-only. RLS previene UPDATE/DELETE.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ops.audit_logs")
    op.execute("DROP TABLE IF EXISTS ops.export_logs")
