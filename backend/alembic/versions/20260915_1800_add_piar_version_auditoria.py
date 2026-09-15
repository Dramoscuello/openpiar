# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Permite auditar versiones del PIAR (finalización/versionado).

Revision ID: d4f1a7b2c8e9
Revises: c3d9e5f1a2b4
Create Date: 2026-09-15 18:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f1a7b2c8e9"
down_revision: Union[str, None] = "c3d9e5f1a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENTIDADES_SIN_VERSION = (
    "'ajuste_razonable', 'acta_acuerdo', "
    "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', 'evidencia_ajuste'"
)
ENTIDADES_CON_VERSION = (
    "'ajuste_razonable', 'acta_acuerdo', "
    "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', "
    "'piar_version', 'evidencia_ajuste'"
)


def _recrear_constraint(entidades: str) -> None:
    op.execute("ALTER TABLE auditoria_cambios DROP CONSTRAINT IF EXISTS ck_auditoria_entidad_tipo")
    op.create_check_constraint(
        "ck_auditoria_entidad_tipo",
        "auditoria_cambios",
        sa.text(f"entidad_tipo IN ({entidades})"),
    )


def upgrade() -> None:
    _recrear_constraint(ENTIDADES_CON_VERSION)


def downgrade() -> None:
    op.execute("DELETE FROM auditoria_cambios WHERE entidad_tipo = 'piar_version'")
    _recrear_constraint(ENTIDADES_SIN_VERSION)
