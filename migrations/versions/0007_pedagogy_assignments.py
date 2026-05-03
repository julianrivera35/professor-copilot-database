"""pedagogy assignments

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-03 00:00:07 UTC

Crea pedagogy.assignments — el trabajo académico creado por el profesor.

Puntos clave:
  · rubric_raw   = texto original del profesor (inmutable)
  · rubric_parsed = JSON estructurado que usa la IA
  · ai_params_snapshot = snapshot del modelo/temperatura/prompt al momento de crear
    la tarea → garantiza reproducibilidad auditabile incluso si cambia el modelo default
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE pedagogy.assignments (
            id                  UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id             UUID              NOT NULL
                                                     REFERENCES auth.users (id)
                                                     ON DELETE RESTRICT,
            ai_model_config_id  UUID              REFERENCES core.ai_model_configs (id)
                                                     ON DELETE SET NULL,

            -- Información académica
            title               TEXT              NOT NULL,
            description         TEXT,
            course_name         TEXT,
            semester            TEXT,

            -- Rúbrica dual
            rubric_raw          TEXT              NOT NULL,
            rubric_parsed       JSONB,

            -- Estado del flujo
            status              assignment_status NOT NULL DEFAULT 'draft',

            -- Trabajos grupales
            is_group_assignment BOOLEAN           NOT NULL DEFAULT FALSE,
            max_group_size      SMALLINT
                                    CHECK (max_group_size BETWEEN 2 AND 20),

            -- Calificación
            max_score           NUMERIC(6, 2)     NOT NULL DEFAULT 100,
            grading_language    TEXT              NOT NULL DEFAULT 'es',
            feedback_language   TEXT              NOT NULL DEFAULT 'es',

            -- Snapshot inmutable de parámetros IA (reproducibilidad y auditoría)
            ai_params_snapshot  JSONB             NOT NULL DEFAULT '{}',

            -- Auditoría
            created_at          TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            deleted_at          TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE INDEX idx_assignments_user
            ON pedagogy.assignments (user_id, status)
            WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE INDEX idx_assignments_status
            ON pedagogy.assignments (status, created_at)
    """)
    # Índice de búsqueda de texto completo en español
    op.execute("""
        CREATE INDEX idx_assignments_search
            ON pedagogy.assignments
            USING GIN (to_tsvector('spanish', title || ' ' || COALESCE(course_name, '')))
    """)

    op.execute("""
        COMMENT ON TABLE pedagogy.assignments IS
            'Tarea/trabajo académico creado por el profesor con su rúbrica.'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.assignments.rubric_raw IS
            'Texto original del profesor, sin procesar.'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.assignments.rubric_parsed IS
            '[{criterion, max_points, description, weight?}]'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.assignments.ai_params_snapshot IS
            'Snapshot inmutable: modelo, temperatura, prompt usado. Garantiza reproducibilidad.'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pedagogy.assignments")
