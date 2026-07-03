# fix auditoria_cambios constraint para incluir evidencia_ajuste
# Revision ID: fix_auditoria_constraint
# Revises: 64d5823839b1
# Create Date: 2026-07-03

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fix_auditoria_constraint'
down_revision: Union[str, None] = '64d5823839b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE auditoria_cambios DROP CONSTRAINT IF EXISTS ck_auditoria_entidad_tipo")
    op.create_check_constraint(
        "ck_auditoria_entidad_tipo",
        "auditoria_cambios",
        sa.text(
            "entidad_tipo IN ('ajuste_razonable', 'recomendacion_pmi', 'acta_acuerdo', "
            "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', 'evidencia_ajuste')"
        ),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE auditoria_cambios DROP CONSTRAINT IF EXISTS ck_auditoria_entidad_tipo")
    op.create_check_constraint(
        "ck_auditoria_entidad_tipo",
        "auditoria_cambios",
        sa.text(
            "entidad_tipo IN ('ajuste_razonable', 'recomendacion_pmi', 'acta_acuerdo', "
            "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado')"
        ),
    )
