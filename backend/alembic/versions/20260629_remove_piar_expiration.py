# remove PIAR expiration: drop fecha_limite_firma, migrate vencido → firmado, update ck_piars_estado
# Revision ID: a1b2c3d4e5f6
# Revises: 95b7f7656d79
# Create Date: 2026-06-29

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '95b7f7656d79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE piars SET estado = 'firmado' WHERE estado = 'vencido'")
    )

    op.drop_constraint("ck_piars_estado", "piars", type_="check")

    op.create_check_constraint(
        "ck_piars_estado",
        "piars",
        "estado IN ('borrador', 'generando_ia', 'en_revision', 'firmado')",
    )

    op.drop_column("piars", "fecha_limite_firma")


def downgrade() -> None:
    op.add_column(
        "piars",
        sa.Column("fecha_limite_firma", sa.Date(), nullable=True),
    )

    op.drop_constraint("ck_piars_estado", "piars", type_="check")

    op.create_check_constraint(
        "ck_piars_estado",
        "piars",
        "estado IN ('borrador', 'generando_ia', 'en_revision', 'firmado', 'vencido')",
    )
