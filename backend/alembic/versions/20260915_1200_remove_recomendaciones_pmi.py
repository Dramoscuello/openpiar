# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Elimina las recomendaciones PMI del PIAR (no hacen parte del formato oficial).

Revision ID: b7e4c1a9d2f3
Revises: 4f7b2d91c6a0
Create Date: 2026-09-15 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7e4c1a9d2f3"
down_revision: Union[str, None] = "4f7b2d91c6a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENTIDADES_SIN_PMI = (
    "'ajuste_razonable', 'acta_acuerdo', "
    "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', 'evidencia_ajuste'"
)
ENTIDADES_CON_PMI = (
    "'ajuste_razonable', 'recomendacion_pmi', 'acta_acuerdo', "
    "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', 'evidencia_ajuste'"
)


def _has_table(table_name: str) -> bool:
    if op.get_context().as_sql:
        return False
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _recrear_constraint(entidades: str) -> None:
    op.execute("ALTER TABLE auditoria_cambios DROP CONSTRAINT IF EXISTS ck_auditoria_entidad_tipo")
    op.create_check_constraint(
        "ck_auditoria_entidad_tipo",
        "auditoria_cambios",
        sa.text(f"entidad_tipo IN ({entidades})"),
    )


def upgrade() -> None:
    # Los registros históricos de PMI dejan de ser válidos al retirar la entidad.
    op.execute("DELETE FROM auditoria_cambios WHERE entidad_tipo = 'recomendacion_pmi'")
    _recrear_constraint(ENTIDADES_SIN_PMI)

    if _has_table("recomendaciones_pmi"):
        op.drop_index("recomendaciones_pmi_piar_id_idx", table_name="recomendaciones_pmi")
        op.drop_table("recomendaciones_pmi")


def downgrade() -> None:
    if not _has_table("recomendaciones_pmi"):
        op.create_table(
            "recomendaciones_pmi",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("actor", sa.Text(), nullable=False),
            sa.Column("acciones", sa.Text(), nullable=False),
            sa.Column("estrategias_implementar", sa.Text(), nullable=False),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "actor IN ('Familia', 'Docentes', 'Directivos', 'Administrativos', 'Pares')",
                name="ck_recomendaciones_actor",
            ),
            sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("recomendaciones_pmi_piar_id_idx", "recomendaciones_pmi", ["piar_id"])

    _recrear_constraint(ENTIDADES_CON_PMI)
