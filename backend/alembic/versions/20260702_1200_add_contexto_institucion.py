# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Añade contexto_institucion a configuracion_sistema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_1200"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "configuracion_sistema",
        sa.Column("contexto_institucion", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuracion_sistema", "contexto_institucion")
