"""pedagogy submissions and grades

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-03 00:00:08 UTC

Crea:
  · pedagogy.submissions — archivos subidos por estudiantes (pipeline 2 fases)
  · pedagogy.grades      — resultado de la calificación IA

También agrega la FK faltante en billing.token_transactions → pedagogy.grades
(que no se podía crear en 0004 porque grades aún no existía).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pedagogy.submissions ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE pedagogy.submissions (
            id                    UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
            assignment_id         UUID              NOT NULL
                                                       REFERENCES pedagogy.assignments (id)
                                                       ON DELETE CASCADE,

            -- Autoría extraída por la IA del documento
            student_name          TEXT,
            student_email         TEXT,
            group_name            TEXT,
            group_members         TEXT[],

            -- Archivo original
            source_filename       TEXT              NOT NULL,
            storage_path          TEXT              NOT NULL,
            file_type             TEXT              NOT NULL
                                                       CHECK (file_type IN ('pdf', 'docx', 'txt')),
            file_size_bytes       INTEGER           NOT NULL,
            file_checksum         TEXT,

            -- Pipeline fase 1: extracción de texto
            extraction_status     extraction_status NOT NULL DEFAULT 'pending',
            extracted_text        TEXT,
            extracted_text_tokens INTEGER,

            -- Pipeline fase 2: calificación IA
            processing_status     processing_status NOT NULL DEFAULT 'pending',
            error_message         TEXT,
            retry_count           SMALLINT          NOT NULL DEFAULT 0,

            processed_at          TIMESTAMPTZ,
            created_at            TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMPTZ       NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE INDEX idx_submissions_assignment
            ON pedagogy.submissions (assignment_id, processing_status)
    """)
    op.execute("""
        CREATE INDEX idx_submissions_pending
            ON pedagogy.submissions (processing_status, created_at)
            WHERE processing_status IN ('pending', 'queued')
    """)
    op.execute("""
        CREATE INDEX idx_submissions_student
            ON pedagogy.submissions (student_name text_pattern_ops)
    """)

    op.execute("""
        COMMENT ON TABLE pedagogy.submissions IS
            'Archivos subidos por estudiantes. Pipeline: extracción → procesamiento → calificación.'
    """)

    # ── pedagogy.grades ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE pedagogy.grades (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            submission_id        UUID         NOT NULL
                                                  REFERENCES pedagogy.submissions (id)
                                                  ON DELETE CASCADE,
            assignment_id        UUID         NOT NULL
                                                  REFERENCES pedagogy.assignments (id)
                                                  ON DELETE CASCADE,

            -- Puntuación
            total_score          NUMERIC(6, 2) NOT NULL,
            max_score            NUMERIC(6, 2) NOT NULL,
            percentage           NUMERIC(5, 2) GENERATED ALWAYS AS
                                     (ROUND((total_score / NULLIF(max_score, 0)) * 100, 2)) STORED,

            -- Desglose por criterio: [{criterion, score, max_points, feedback}]
            rubric_scores        JSONB         NOT NULL DEFAULT '[]',

            -- Retroalimentación textual
            general_feedback     TEXT          NOT NULL,
            strengths            TEXT,
            areas_for_improvement TEXT,

            -- Trazabilidad de costos IA
            tokens_input         INTEGER,
            tokens_output        INTEGER,
            ai_cost_cents        NUMERIC(10, 4),
            model_used           TEXT          NOT NULL,
            model_version        TEXT,
            token_source         token_source  NOT NULL DEFAULT 'platform',

            -- Control de calidad docente
            is_reviewed          BOOLEAN       NOT NULL DEFAULT FALSE,
            is_published         BOOLEAN       NOT NULL DEFAULT FALSE,
            reviewed_at          TIMESTAMPTZ,
            published_at         TIMESTAMPTZ,

            created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

            CONSTRAINT uq_grades_submission UNIQUE (submission_id)
        )
    """)

    op.execute("""
        CREATE INDEX idx_grades_assignment
            ON pedagogy.grades (assignment_id, is_published)
    """)
    op.execute("""
        CREATE INDEX idx_grades_percentage
            ON pedagogy.grades (assignment_id, percentage DESC)
    """)

    op.execute("""
        COMMENT ON TABLE pedagogy.grades IS
            'Resultado de la calificación IA. percentage es columna generada automáticamente.'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.grades.rubric_scores IS
            '[{criterion, score, max_points, feedback}] — desglose por criterio.'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.grades.percentage IS
            'Columna GENERATED: (total_score / max_score) * 100. No editar directamente.'
    """)
    op.execute("""
        COMMENT ON COLUMN pedagogy.grades.token_source IS
            'platform = descontado del wallet; own_key = el usuario pagó directo al proveedor.'
    """)

    # ── FK diferida: token_transactions.grade_id → grades ────────────────────
    op.execute("""
        ALTER TABLE billing.token_transactions
            ADD CONSTRAINT fk_token_tx_grade
            FOREIGN KEY (grade_id)
            REFERENCES pedagogy.grades (id)
            ON DELETE SET NULL
    """)


def downgrade() -> None:
    # Primero quitar la FK diferida
    op.execute("""
        ALTER TABLE billing.token_transactions
            DROP CONSTRAINT IF EXISTS fk_token_tx_grade
    """)
    op.execute("DROP TABLE IF EXISTS pedagogy.grades")
    op.execute("DROP TABLE IF EXISTS pedagogy.submissions")
