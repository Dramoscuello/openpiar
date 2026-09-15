# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""PIAR por periodo académico: año lectivo, cobertura, acta, versiones y estado.

Revision ID: c3d9e5f1a2b4
Revises: b7e4c1a9d2f3
Create Date: 2026-09-15 15:00:00
"""

from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d9e5f1a2b4"
down_revision: Union[str, None] = "b7e4c1a9d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, nombre: str) -> bool:
    return nombre in sa.inspect(bind).get_table_names()


def _has_column(bind, tabla: str, columna: str) -> bool:
    inspector = sa.inspect(bind)
    return any(c["name"] == columna for c in inspector.get_columns(tabla))


def _crear_periodo_fallback(bind, anio: int) -> int:
    return bind.execute(
        sa.text(
            """
            INSERT INTO periodos_academicos (nombre, activo, anio_lectivo, fecha_inicio, fecha_fin)
            VALUES (:nombre, false, :anio, :inicio, :fin)
            RETURNING id
            """
        ),
        {
            "nombre": f"Periodo {anio}",
            "anio": anio,
            "inicio": date(anio, 1, 1),
            "fin": date(anio, 12, 31),
        },
    ).scalar()


def _periodo_fallback(bind, anio: int, cache: dict) -> int:
    periodos = bind.execute(
        sa.text(
            "SELECT id, anio_lectivo, activo FROM periodos_academicos ORDER BY fecha_inicio"
        )
    ).mappings().all()
    activo = next((p for p in periodos if p["activo"]), None)
    if activo:
        return activo["id"]
    del_mismo_anio = next((p for p in periodos if p["anio_lectivo"] == anio), None)
    if del_mismo_anio:
        return del_mismo_anio["id"]
    if periodos:
        return periodos[0]["id"]
    if cache.get("fallback") is None:
        cache["fallback"] = _crear_periodo_fallback(bind, anio)
    return cache["fallback"]


def _periodo_ultimo_ajuste(bind, piar_id) -> Union[int, None]:
    return bind.execute(
        sa.text(
            """
            SELECT periodo_id FROM ajustes_razonables
            WHERE piar_id = :piar_id
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ),
        {"piar_id": piar_id},
    ).scalar()


def _anio_piar(piars_anio: dict, piar_id) -> int:
    return piars_anio.get(piar_id) or date.today().year


def _backfill_cobertura(bind, piars_anio: dict, cache: dict) -> None:
    ajustes = bind.execute(
        sa.text(
            """
            SELECT piar_id, asignatura_id, periodo_id
            FROM ajustes_razonables
            WHERE asignatura_id IS NOT NULL
            ORDER BY updated_at
            """
        )
    ).fetchall()
    periodos_por_asignatura: dict[tuple, list[int]] = {}
    for piar_id, asignatura_id, periodo_id in ajustes:
        lista = periodos_por_asignatura.setdefault((piar_id, asignatura_id), [])
        if periodo_id not in lista:
            lista.append(periodo_id)

    filas = bind.execute(
        sa.text("SELECT id, piar_id, asignatura_id FROM piar_asignaturas")
    ).fetchall()
    for fila_id, piar_id, asignatura_id in filas:
        periodos = list(periodos_por_asignatura.get((piar_id, asignatura_id)) or [])
        if not periodos:
            periodos = [_periodo_fallback(bind, _anio_piar(piars_anio, piar_id), cache)]
        bind.execute(
            sa.text("UPDATE piar_asignaturas SET periodo_id = :pid WHERE id = :id"),
            {"pid": periodos[0], "id": fila_id},
        )
        for periodo_id in periodos[1:]:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO piar_asignaturas (
                        id, piar_id, periodo_id, asignatura_id, docente_id,
                        nombre_asignatura, area_nombre, docente_nombre, estado,
                        justificacion, updated_at
                    )
                    SELECT gen_random_uuid(), piar_id, :pid, asignatura_id, docente_id,
                           nombre_asignatura, area_nombre, docente_nombre, estado,
                           justificacion, now()
                    FROM piar_asignaturas WHERE id = :origen
                    """
                ),
                {"pid": periodo_id, "origen": fila_id},
            )


def _backfill_actas(bind, piars_anio: dict, cache: dict) -> None:
    actas = bind.execute(sa.text("SELECT id, piar_id FROM actas_acuerdo")).fetchall()
    for acta_id, piar_id in actas:
        periodo_id = _periodo_ultimo_ajuste(bind, piar_id) or _periodo_fallback(
            bind, _anio_piar(piars_anio, piar_id), cache
        )
        bind.execute(
            sa.text("UPDATE actas_acuerdo SET periodo_id = :pid WHERE id = :id"),
            {"pid": periodo_id, "id": acta_id},
        )


def _backfill_versiones(bind, piars_anio: dict, cache: dict) -> None:
    versiones = bind.execute(sa.text("SELECT id, piar_id FROM piar_versiones")).fetchall()
    for version_id, piar_id in versiones:
        periodo_id = _periodo_ultimo_ajuste(bind, piar_id) or _periodo_fallback(
            bind, _anio_piar(piars_anio, piar_id), cache
        )
        bind.execute(
            sa.text("UPDATE piar_versiones SET periodo_id = :pid WHERE id = :id"),
            {"pid": periodo_id, "id": version_id},
        )


def _backfill_piar_periodos(bind, piars_anio: dict, cache: dict) -> None:
    piars = bind.execute(sa.text("SELECT id, estado FROM piars")).fetchall()
    for piar_id, estado in piars:
        periodos = bind.execute(
            sa.text(
                """
                SELECT DISTINCT periodo_id FROM ajustes_razonables WHERE piar_id = :piar_id
                UNION
                SELECT DISTINCT periodo_id FROM piar_asignaturas WHERE piar_id = :piar_id
                UNION
                SELECT periodo_id FROM actas_acuerdo WHERE piar_id = :piar_id
                """
            ),
            {"piar_id": piar_id},
        ).scalars().all()
        if not periodos:
            periodos = [_periodo_fallback(bind, _anio_piar(piars_anio, piar_id), cache)]

        periodo_firmado = None
        if estado == "firmado":
            periodo_firmado = bind.execute(
                sa.text(
                    """
                    SELECT periodo_id FROM piar_versiones
                    WHERE piar_id = :piar_id ORDER BY numero DESC LIMIT 1
                    """
                ),
                {"piar_id": piar_id},
            ).scalar()

        for periodo_id in periodos:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO piar_periodos (id, piar_id, periodo_id, estado)
                    VALUES (gen_random_uuid(), :piar_id, :periodo_id, :estado)
                    ON CONFLICT (piar_id, periodo_id) DO NOTHING
                    """
                ),
                {
                    "piar_id": piar_id,
                    "periodo_id": periodo_id,
                    "estado": "firmado" if periodo_id == periodo_firmado else "borrador",
                },
            )


def upgrade() -> None:
    bind = op.get_bind()
    cache: dict = {}

    # 1. Año lectivo de los periodos
    if not _has_column(bind, "periodos_academicos", "anio_lectivo"):
        op.add_column(
            "periodos_academicos",
            sa.Column("anio_lectivo", sa.Integer(), nullable=True),
        )
        op.execute(
            "UPDATE periodos_academicos SET anio_lectivo = EXTRACT(YEAR FROM fecha_inicio)::int"
        )
        op.alter_column("periodos_academicos", "anio_lectivo", nullable=False)

    piars_anio = dict(bind.execute(sa.text("SELECT id, anio_lectivo FROM piars")).fetchall())

    # 2. Cobertura por periodo
    if not _has_column(bind, "piar_asignaturas", "periodo_id"):
        op.add_column(
            "piar_asignaturas",
            sa.Column("periodo_id", sa.BigInteger(), nullable=True),
        )
        _backfill_cobertura(bind, piars_anio, cache)
        op.alter_column("piar_asignaturas", "periodo_id", nullable=False)
        op.create_foreign_key(
            "fk_piar_asignaturas_periodo",
            "piar_asignaturas",
            "periodos_academicos",
            ["periodo_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.execute("ALTER TABLE piar_asignaturas DROP CONSTRAINT IF EXISTS uq_piar_asignatura")
        op.create_unique_constraint(
            "uq_piar_asignatura_periodo",
            "piar_asignaturas",
            ["piar_id", "periodo_id", "asignatura_id"],
        )
        op.create_index("piar_asignaturas_periodo_idx", "piar_asignaturas", ["periodo_id"])

    # 3. Acta completa por periodo
    if not _has_column(bind, "actas_acuerdo", "periodo_id"):
        op.add_column(
            "actas_acuerdo",
            sa.Column("periodo_id", sa.BigInteger(), nullable=True),
        )
        _backfill_actas(bind, piars_anio, cache)
        op.alter_column("actas_acuerdo", "periodo_id", nullable=False)
        op.create_foreign_key(
            "fk_actas_acuerdo_periodo",
            "actas_acuerdo",
            "periodos_academicos",
            ["periodo_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.execute("ALTER TABLE actas_acuerdo DROP CONSTRAINT IF EXISTS actas_acuerdo_piar_id_key")
        op.create_unique_constraint(
            "uq_acta_acuerdo_piar_periodo",
            "actas_acuerdo",
            ["piar_id", "periodo_id"],
        )
        op.create_index("actas_acuerdo_piar_id_idx", "actas_acuerdo", ["piar_id"])
        op.create_index("actas_acuerdo_periodo_id_idx", "actas_acuerdo", ["periodo_id"])

    # 4. Versiones por periodo
    if not _has_column(bind, "piar_versiones", "periodo_id"):
        op.add_column(
            "piar_versiones",
            sa.Column("periodo_id", sa.BigInteger(), nullable=True),
        )
        _backfill_versiones(bind, piars_anio, cache)
        op.create_foreign_key(
            "fk_piar_versiones_periodo",
            "piar_versiones",
            "periodos_academicos",
            ["periodo_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("piar_versiones_periodo_idx", "piar_versiones", ["periodo_id"])

    # 5. Estado del PIAR por periodo
    if not _has_table(bind, "piar_periodos"):
        op.create_table(
            "piar_periodos",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("periodo_id", sa.BigInteger(), nullable=False),
            sa.Column("estado", sa.Text(), nullable=False, server_default="borrador"),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "estado IN ('borrador', 'en_revision', 'firmado')",
                name="ck_piar_periodos_estado",
            ),
            sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["periodo_id"], ["periodos_academicos.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("piar_id", "periodo_id", name="uq_piar_periodo"),
        )
        op.create_index("piar_periodos_piar_id_idx", "piar_periodos", ["piar_id"])
        op.create_index("piar_periodos_periodo_id_idx", "piar_periodos", ["periodo_id"])

    # El backfill es idempotente y también cubre tablas creadas por create_all.
    _backfill_piar_periodos(bind, piars_anio, cache)


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "piar_periodos"):
        op.drop_table("piar_periodos")

    if _has_column(bind, "piar_versiones", "periodo_id"):
        op.drop_index("piar_versiones_periodo_idx", table_name="piar_versiones")
        op.drop_constraint("fk_piar_versiones_periodo", "piar_versiones", type_="foreignkey")
        op.drop_column("piar_versiones", "periodo_id")

    if _has_column(bind, "actas_acuerdo", "periodo_id"):
        op.drop_index("actas_acuerdo_periodo_id_idx", table_name="actas_acuerdo")
        op.drop_index("actas_acuerdo_piar_id_idx", table_name="actas_acuerdo")
        op.drop_constraint("uq_acta_acuerdo_piar_periodo", "actas_acuerdo", type_="unique")
        op.drop_constraint("fk_actas_acuerdo_periodo", "actas_acuerdo", type_="foreignkey")
        op.execute(
            """
            DELETE FROM actas_acuerdo a
            USING actas_acuerdo b
            WHERE a.piar_id = b.piar_id AND a.id <> b.id
              AND (a.created_at, a.id) < (b.created_at, b.id)
            """
        )
        op.drop_column("actas_acuerdo", "periodo_id")
        op.create_unique_constraint("actas_acuerdo_piar_id_key", "actas_acuerdo", ["piar_id"])

    if _has_column(bind, "piar_asignaturas", "periodo_id"):
        op.drop_index("piar_asignaturas_periodo_idx", table_name="piar_asignaturas")
        op.drop_constraint("uq_piar_asignatura_periodo", "piar_asignaturas", type_="unique")
        op.drop_constraint("fk_piar_asignaturas_periodo", "piar_asignaturas", type_="foreignkey")
        op.execute(
            """
            DELETE FROM piar_asignaturas a
            USING piar_asignaturas b
            WHERE a.piar_id = b.piar_id AND a.asignatura_id = b.asignatura_id
              AND a.id <> b.id AND (a.updated_at, a.id) < (b.updated_at, b.id)
            """
        )
        op.drop_column("piar_asignaturas", "periodo_id")
        op.create_unique_constraint("uq_piar_asignatura", "piar_asignaturas", ["piar_id", "asignatura_id"])

    if _has_column(bind, "periodos_academicos", "anio_lectivo"):
        op.drop_column("periodos_academicos", "anio_lectivo")
