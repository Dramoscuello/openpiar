# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Añade versión de sesión en usuarios y tabla de refresh tokens con rotación.

Revision ID: e5a2b8c4d6f0
Revises: d4f1a7b2c8e9
Create Date: 2026-10-07 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e5a2b8c4d6f0"
down_revision: Union[str, None] = "d4f1a7b2c8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tiene_columna(tabla: str, columna: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return columna in {c["name"] for c in inspector.get_columns(tabla)}


def _tiene_tabla(tabla: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return tabla in inspector.get_table_names()


def upgrade() -> None:
    # Idempotente: una BD creada con create_all puede tener ya la tabla.
    if not _tiene_columna("usuarios", "token_version"):
        op.add_column(
            "usuarios",
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if not _tiene_tabla("refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "usuario_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
            sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("replaced_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("ip", sa.Text(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "refresh_tokens_usuario_id_idx", "refresh_tokens", ["usuario_id"]
        )
        op.create_index(
            "refresh_tokens_family_id_idx", "refresh_tokens", ["family_id"]
        )
        op.create_index(
            "refresh_tokens_expires_at_idx", "refresh_tokens", ["expires_at"]
        )


def downgrade() -> None:
    if _tiene_tabla("refresh_tokens"):
        op.drop_index("refresh_tokens_expires_at_idx", table_name="refresh_tokens")
        op.drop_index("refresh_tokens_family_id_idx", table_name="refresh_tokens")
        op.drop_index("refresh_tokens_usuario_id_idx", table_name="refresh_tokens")
        op.drop_table("refresh_tokens")
    if _tiene_columna("usuarios", "token_version"):
        op.drop_column("usuarios", "token_version")
