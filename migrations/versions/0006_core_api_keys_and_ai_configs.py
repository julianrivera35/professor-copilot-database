"""core api keys and ai model configs

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03 00:00:06 UTC

Crea:
  · core.api_keys          — claves de API de la plataforma (solo hash, nunca texto plano)
  · core.ai_model_configs  — catálogo de modelos IA con costos reales por token
  · core.user_ai_preferences — preferencias por usuario, incluye modo BYOK
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── core.api_keys ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.api_keys (
            id           UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id      UUID    NOT NULL
                                     REFERENCES auth.users (id)
                                     ON DELETE CASCADE,

            name         TEXT    NOT NULL,
            -- Solo guardamos el hash; texto plano se muestra una sola vez
            key_hash     TEXT    NOT NULL,
            -- Prefijo visible para identificación ('sk-abc12...')
            key_prefix   CHAR(12) NOT NULL,

            -- Permisos granulares
            scopes       TEXT[]  NOT NULL
                                     DEFAULT ARRAY['grade:write', 'assignment:read'],

            last_used_at TIMESTAMPTZ,
            expires_at   TIMESTAMPTZ,
            revoked_at   TIMESTAMPTZ,

            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("CREATE UNIQUE INDEX uq_api_keys_hash ON core.api_keys (key_hash)")
    op.execute("""
        CREATE INDEX idx_api_keys_user
            ON core.api_keys (user_id)
            WHERE revoked_at IS NULL
    """)

    op.execute("""
        COMMENT ON TABLE core.api_keys IS
            'Claves de API de la plataforma. key_hash = SHA-256; key_prefix visible al usuario.'
    """)

    # ── core.ai_model_configs ─────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.ai_model_configs (
            id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            provider             ai_provider NOT NULL,
            model_id             TEXT        NOT NULL,
            display_name         TEXT        NOT NULL,

            -- Límites técnicos
            max_context_tokens   INTEGER     NOT NULL,

            -- Costos reales para reporting (USD por 1k tokens)
            cost_per_1k_input    NUMERIC(10, 6) NOT NULL DEFAULT 0,
            cost_per_1k_output   NUMERIC(10, 6) NOT NULL DEFAULT 0,

            -- Control
            is_active            BOOLEAN     NOT NULL DEFAULT TRUE,
            is_default           BOOLEAN     NOT NULL DEFAULT FALSE,

            -- Capacidades extendidas sin migración
            capabilities         JSONB       NOT NULL DEFAULT '{}',

            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Solo un modelo puede ser el default activo a la vez
    op.execute("""
        CREATE UNIQUE INDEX uq_ai_models_default
            ON core.ai_model_configs (is_default)
            WHERE is_default = TRUE AND is_active = TRUE
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_ai_models_provider_model
            ON core.ai_model_configs (provider, model_id)
    """)

    op.execute("""
        COMMENT ON TABLE core.ai_model_configs IS
            'Catálogo de modelos IA disponibles con costos reales por token.'
    """)

    # ── core.user_ai_preferences ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.user_ai_preferences (
            id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id                 UUID        NOT NULL
                                                    REFERENCES auth.users (id)
                                                    ON DELETE CASCADE,
            ai_model_config_id      UUID        REFERENCES core.ai_model_configs (id)
                                                    ON DELETE SET NULL,

            -- Parámetros de generación
            temperature             NUMERIC(3, 2) NOT NULL DEFAULT 0.30
                                                    CHECK (temperature BETWEEN 0 AND 2),
            max_tokens_response     INTEGER       NOT NULL DEFAULT 2000
                                                    CHECK (max_tokens_response BETWEEN 256 AND 8000),

            -- Preferencias de idioma y tono
            feedback_language       TEXT          NOT NULL DEFAULT 'es',
            feedback_tone           TEXT          NOT NULL DEFAULT 'formal',

            -- Prompt personalizado
            use_custom_prompt       BOOLEAN       NOT NULL DEFAULT FALSE,
            system_prompt_override  TEXT,

            -- Modo BYOK (Bring Your Own Key)
            -- Si activo: backend usa own_api_key_encrypted, no descuenta del wallet
            use_own_api_key         BOOLEAN       NOT NULL DEFAULT FALSE,
            own_api_key_encrypted   TEXT,
            own_api_key_provider    ai_provider,
            own_api_key_verified    BOOLEAN       NOT NULL DEFAULT FALSE,
            own_api_key_verified_at TIMESTAMPTZ,

            updated_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_user_ai_prefs UNIQUE (user_id)
        )
    """)

    op.execute("""
        COMMENT ON TABLE core.user_ai_preferences IS
            'Preferencias IA por usuario. use_own_api_key activa modo BYOK sin consumir wallet.'
    """)
    op.execute("""
        COMMENT ON COLUMN core.user_ai_preferences.use_own_api_key IS
            'Si TRUE, usa own_api_key_encrypted. No descuenta del wallet.'
    """)
    op.execute("""
        COMMENT ON COLUMN core.user_ai_preferences.own_api_key_encrypted IS
            'AES-256 en capa de aplicación. Nunca en texto plano.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS core.user_ai_preferences")
    op.execute("DROP TABLE IF EXISTS core.ai_model_configs")
    op.execute("DROP TABLE IF EXISTS core.api_keys")
