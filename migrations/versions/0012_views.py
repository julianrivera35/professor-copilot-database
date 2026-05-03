"""views

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-03 00:00:12 UTC

Crea las vistas de reporting:
  · pedagogy.v_grades_export  — vista plana para exportación CSV de calificaciones
  · billing.v_usage_summary   — resumen de uso por usuario para panel admin
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── pedagogy.v_grades_export ──────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE VIEW pedagogy.v_grades_export AS
        SELECT
            a.title                    AS assignment_title,
            a.course_name,
            a.semester,
            s.student_name,
            s.student_email,
            s.group_name,
            s.group_members,
            s.source_filename,
            g.total_score,
            g.max_score,
            g.percentage,
            g.general_feedback,
            g.strengths,
            g.areas_for_improvement,
            g.rubric_scores,
            g.is_published,
            g.created_at               AS graded_at
        FROM pedagogy.grades g
        JOIN pedagogy.submissions s ON s.id = g.submission_id
        JOIN pedagogy.assignments a ON a.id = g.assignment_id
    """)

    # ── billing.v_usage_summary ───────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE VIEW billing.v_usage_summary AS
        SELECT
            u.id                        AS user_id,
            u.email,
            u.full_name,
            p.name                      AS plan_name,
            sub.status                  AS subscription_status,
            q.period_year,
            q.period_month,
            q.assignments_used,
            q.students_processed,
            q.tokens_consumed,
            w.balance_free,
            w.balance_paid,
            w.balance_total,
            w.total_tokens_purchased,
            w.total_tokens_consumed     AS lifetime_tokens_consumed,
            p.max_assignments_per_month,
            p.max_students_per_assignment
        FROM auth.users u
        LEFT JOIN billing.subscriptions sub
               ON sub.user_id = u.id
              AND sub.status IN ('active', 'trialing')
        LEFT JOIN billing.plans p
               ON p.id = sub.plan_id
        LEFT JOIN billing.usage_quotas q
               ON q.user_id = u.id
              AND q.period_year  = EXTRACT(YEAR  FROM NOW())
              AND q.period_month = EXTRACT(MONTH FROM NOW())
        LEFT JOIN billing.token_wallet w
               ON w.user_id = u.id
        WHERE u.deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS billing.v_usage_summary")
    op.execute("DROP VIEW IF EXISTS pedagogy.v_grades_export")
