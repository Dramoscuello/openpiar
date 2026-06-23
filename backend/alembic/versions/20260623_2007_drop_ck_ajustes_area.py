# drop_ck_ajustes_area
# Revision ID: 728f75c13a3c
# Revises: 61d7be033df6
# Create Date: 2026-06-23 20:07:38.899770+00:00

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '728f75c13a3c'
down_revision: Union[str, None] = '61d7be033df6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop CHECK constraint to allow dynamic areas and asignaturas
    op.drop_constraint("ck_ajustes_area", "ajustes_razonables", type_="check")


def downgrade() -> None:
    # Re-create CHECK constraint
    op.create_check_constraint(
        "ck_ajustes_area",
        "ajustes_razonables",
        "area IN ('Matemáticas', 'Ciencias', 'Lenguaje', 'Convivencia', 'Socialización', 'Participación', 'Autonomía', 'Autocontrol')"
    )
