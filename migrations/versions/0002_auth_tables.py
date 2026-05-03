"""auth tables: users and user_sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03 00:00:02 UTC

Crea auth.users (núcleo de identidad) y auth.user_sessions (sesiones multi-device).

Seguridad:
  · password_hash: bcrypt con factor >= 12 (enforced en capa de aplicación)
  · mfa_secret:    AES-256 en capa de aplicación antes de persistir
  · token_hash:    SHA-256 hex (nunca el token en texto plano)
  · locked_until:  bloqueo automático tras intentos fallidos (sin lógica extra en backend)
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── auth.users ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE auth.users (
            id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            email                TEXT        NOT NULL,
            password_hash        TEXT        NOT NULL,
            full_name            TEXT        NOT NULL,
            role                 user_role   NOT NULL DEFAULT 'teacher',
            status               user_status NOT NULL DEFAULT 'pending_verification',

            -- Verificación de email
            email_verified_at    TIMESTAMPTZ,
            email_verify_token   TEXT,

            -- Autenticación multifactor
            mfa_enabled          BOOLEAN     NOT NULL DEFAULT FALSE,
            mfa_secret           TEXT,
            mfa_backup_codes     TEXT[],

            -- Perfil
            avatar_url           TEXT,
            timezone             TEXT        NOT NULL DEFAULT 'America/Bogota',
            locale               TEXT        NOT NULL DEFAULT 'es',

            -- Control de acceso
            last_login_at        TIMESTAMPTZ,
            failed_login_count   SMALLINT    NOT NULL DEFAULT 0,
            locked_until         TIMESTAMPTZ,

            -- Auditoría
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at           TIMESTAMPTZ
        )
    """)

    # Unicidad solo sobre emails activos (permite re-registro tras soft delete)
    op.execute("""
        CREATE UNIQUE INDEX uq_users_email_active
            ON auth.users (email)
            WHERE deleted_at IS NULL
    """)
    op.execute("CREATE INDEX idx_users_status     ON auth.users (status)")
    op.execute("CREATE INDEX idx_users_deleted_at ON auth.users (deleted_at)")

    # Comentarios de documentación
    op.execute("""
        COMMENT ON TABLE auth.users IS
            'Profesores y administradores. Soft delete via deleted_at.'
    """)
    op.execute("""
        COMMENT ON COLUMN auth.users.password_hash IS
            'bcrypt con factor de costo >= 12.'
    """)
    op.execute("""
        COMMENT ON COLUMN auth.users.mfa_secret IS
            'Cifrado AES-256 en capa de aplicación antes de persistir.'
    """)

    # ── auth.user_sessions ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE auth.user_sessions (
            id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id              UUID        NOT NULL
                                                REFERENCES auth.users (id)
                                                ON DELETE CASCADE,

            -- Tokens (nunca en texto plano — SHA-256 hex)
            token_hash           TEXT        NOT NULL,
            refresh_token_hash   TEXT,

            -- Metadata de dispositivo
            ip_address           INET,
            user_agent           TEXT,
            device_name          TEXT,

            -- Ciclo de vida
            expires_at           TIMESTAMPTZ NOT NULL,
            revoked_at           TIMESTAMPTZ,

            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_sessions_token
            ON auth.user_sessions (token_hash)
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_sessions_refresh
            ON auth.user_sessions (refresh_token_hash)
            WHERE refresh_token_hash IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX idx_sessions_user_id
            ON auth.user_sessions (user_id, expires_at)
            WHERE revoked_at IS NULL
    """)

    op.execute("""
        COMMENT ON TABLE auth.user_sessions IS
            'Sesiones activas. Solo se guardan hashes de tokens.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth.user_sessions")
    op.execute("DROP TABLE IF EXISTS auth.users")
