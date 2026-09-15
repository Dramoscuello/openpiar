# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Add official PIAR workflow, subject coverage and immutable versions.

Revision ID: 4f7b2d91c6a0
Revises: fdaf717bf93e
Create Date: 2026-09-08 16:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4f7b2d91c6a0"
down_revision: Union[str, None] = "fdaf717bf93e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    if op.get_context().as_sql:
        return False
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if op.get_context().as_sql:
        return False
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _has_constraint(table_name: str, constraint_name: str) -> bool:
    if op.get_context().as_sql:
        return False
    inspector = sa.inspect(op.get_bind())
    constraints = (
        inspector.get_check_constraints(table_name)
        + inspector.get_unique_constraints(table_name)
        + inspector.get_foreign_keys(table_name)
    )
    return any(item.get("name") == constraint_name for item in constraints)


def _has_index(table_name: str, index_name: str) -> bool:
    if op.get_context().as_sql:
        return False
    return any(
        index["name"] == index_name
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    op.alter_column("estudiantes", "departamento_residencia", existing_type=sa.Text(), nullable=True)
    op.alter_column("estudiantes", "municipio_residencia", existing_type=sa.Text(), nullable=True)
    op.alter_column("estudiantes", "direccion", existing_type=sa.Text(), nullable=True)
    op.alter_column("estudiantes", "barrio_vereda", existing_type=sa.Text(), nullable=True)
    op.alter_column("estudiantes", "en_centro_proteccion", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("estudiantes", "victima_conflicto", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("estudiantes", "registro_victima", existing_type=sa.Boolean(), nullable=True)
    _add_column_if_missing("estudiantes", sa.Column("pertenece_grupo_etnico", sa.Boolean(), nullable=True))

    _add_column_if_missing("trayectorias_educativas", sa.Column("vinculado_sistema_anterior", sa.Boolean(), nullable=True))
    _add_column_if_missing("trayectorias_educativas", sa.Column("estado_ultimo_grado", sa.Text(), nullable=True))
    if not _has_constraint("trayectorias_educativas", "ck_trayectorias_estado_ultimo_grado"):
        op.create_check_constraint(
            "ck_trayectorias_estado_ultimo_grado",
            "trayectorias_educativas",
            "estado_ultimo_grado IN ('aprobado', 'reprobado', 'sin_terminar') OR estado_ultimo_grado IS NULL",
        )

    _add_column_if_missing("piars", sa.Column("lugar_diligenciamiento", sa.Text(), nullable=True))
    _add_column_if_missing("piars", sa.Column("version_actual", sa.Integer(), server_default="0", nullable=False))
    if not _has_constraint("piars", "uq_piars_estudiante_anio"):
        op.create_unique_constraint("uq_piars_estudiante_anio", "piars", ["estudiante_id", "anio_lectivo"])

    _add_column_if_missing("caracteristicas_estudiante", sa.Column("entorno_familiar_social_economico", sa.Text(), nullable=True))
    _add_column_if_missing("caracteristicas_estudiante", sa.Column("otras_observaciones", sa.Text(), nullable=True))

    _add_column_if_missing(
        "ajustes_razonables",
        sa.Column("asignatura_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    if not _has_constraint("ajustes_razonables", "fk_ajustes_asignatura"):
        op.create_foreign_key(
            "fk_ajustes_asignatura",
            "ajustes_razonables",
            "asignaturas",
            ["asignatura_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _has_table("piar_participantes"):
        op.create_table(
            "piar_participantes",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("nombre", sa.Text(), nullable=False),
            sa.Column("cargo", sa.Text(), nullable=True),
            sa.Column("area", sa.Text(), nullable=True),
            sa.Column("rol_piar", sa.Text(), nullable=False),
            sa.Column("orden", sa.Integer(), server_default="0", nullable=False),
            sa.Column("confirmado", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.CheckConstraint(
                "rol_piar IN ('director_grupo', 'docente_aula', 'docente_apoyo', 'orientador', 'coordinador')",
                name="ck_piar_participantes_rol",
            ),
            sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index("piar_participantes", "piar_participantes_piar_id_idx"):
        op.create_index("piar_participantes_piar_id_idx", "piar_participantes", ["piar_id"])

    if not _has_table("piar_asignaturas"):
        op.create_table(
            "piar_asignaturas",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("asignatura_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("docente_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("nombre_asignatura", sa.Text(), nullable=False),
            sa.Column("area_nombre", sa.Text(), nullable=True),
            sa.Column("docente_nombre", sa.Text(), nullable=True),
            sa.Column("estado", sa.Text(), server_default="pendiente", nullable=False),
            sa.Column("justificacion", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "estado IN ('pendiente', 'con_ajuste', 'no_requiere')",
                name="ck_piar_asignaturas_estado",
            ),
            sa.ForeignKeyConstraint(["asignatura_id"], ["asignaturas.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["docente_id"], ["usuarios.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("piar_id", "asignatura_id", name="uq_piar_asignatura"),
        )
    if not _has_index("piar_asignaturas", "piar_asignaturas_piar_id_idx"):
        op.create_index("piar_asignaturas_piar_id_idx", "piar_asignaturas", ["piar_id"])

    # Compatibilidad aditiva: completar instantáneas para PIAR existentes sin
    # modificar ni eliminar sus ajustes o firmas históricas.
    op.execute(sa.text("""
        UPDATE piars p
        SET lugar_diligenciamiento = s.nombre
        FROM estudiantes e
        JOIN grupos g ON g.id = e.grupo_id
        JOIN sedes s ON s.id = g.sede_id
        WHERE p.estudiante_id = e.id AND p.lugar_diligenciamiento IS NULL
    """))
    op.execute(sa.text("""
        UPDATE estudiantes
        SET pertenece_grupo_etnico = TRUE
        WHERE pertenece_grupo_etnico IS NULL
          AND NULLIF(BTRIM(grupo_etnico), '') IS NOT NULL
    """))
    op.execute(sa.text("""
        UPDATE trayectorias_educativas
        SET estado_ultimo_grado = CASE
            WHEN aprobo_ultimo_grado THEN 'aprobado' ELSE 'reprobado'
        END
        WHERE estado_ultimo_grado IS NULL
          AND NULLIF(BTRIM(ultimo_grado_cursado), '') IS NOT NULL
    """))
    op.execute(sa.text("""
        INSERT INTO piar_participantes
            (id, piar_id, usuario_id, nombre, cargo, area, rol_piar, orden, confirmado)
        SELECT gen_random_uuid(), p.id, u.id,
               CONCAT_WS(' ', u.nombre, u.apellido), u.cargo, NULL,
               'director_grupo', 0, TRUE
        FROM piars p
        JOIN estudiantes e ON e.id = p.estudiante_id
        JOIN grupos g ON g.id = e.grupo_id
        JOIN usuarios u ON u.id = g.director_id
        WHERE NOT EXISTS (
            SELECT 1 FROM piar_participantes pp
            WHERE pp.piar_id = p.id AND pp.usuario_id = u.id AND pp.rol_piar = 'director_grupo'
        )
    """))
    op.execute(sa.text("""
        INSERT INTO piar_participantes
            (id, piar_id, usuario_id, nombre, cargo, area, rol_piar, orden, confirmado)
        SELECT gen_random_uuid(), p.id, u.id,
               CONCAT_WS(' ', u.nombre, u.apellido), u.cargo, a.nombre,
               'docente_aula', ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY a.nombre), TRUE
        FROM piars p
        JOIN estudiantes e ON e.id = p.estudiante_id
        JOIN carga_academica ca ON ca.grupo_id = e.grupo_id
        JOIN usuarios u ON u.id = ca.docente_id
        JOIN asignaturas a ON a.id = ca.asignatura_id
        WHERE NOT EXISTS (
            SELECT 1 FROM piar_participantes pp
            WHERE pp.piar_id = p.id AND pp.usuario_id = u.id AND pp.area = a.nombre
        )
    """))
    op.execute(sa.text("""
        INSERT INTO piar_asignaturas
            (id, piar_id, asignatura_id, docente_id, nombre_asignatura,
             area_nombre, docente_nombre, estado, justificacion, updated_at)
        SELECT DISTINCT ON (p.id, a.id)
               gen_random_uuid(), p.id, a.id, u.id, a.nombre, ar.nombre,
               CONCAT_WS(' ', u.nombre, u.apellido),
               CASE WHEN EXISTS (
                   SELECT 1 FROM ajustes_razonables aj
                   WHERE aj.piar_id = p.id
                     AND LOWER(BTRIM(aj.area)) = LOWER(BTRIM(a.nombre))
               ) THEN 'con_ajuste' ELSE 'pendiente' END,
               NULL, NOW()
        FROM piars p
        JOIN estudiantes e ON e.id = p.estudiante_id
        JOIN carga_academica ca ON ca.grupo_id = e.grupo_id
        JOIN asignaturas a ON a.id = ca.asignatura_id
        JOIN areas ar ON ar.id = a.area_id
        JOIN usuarios u ON u.id = ca.docente_id
        WHERE NOT EXISTS (
            SELECT 1 FROM piar_asignaturas pa
            WHERE pa.piar_id = p.id AND pa.asignatura_id = a.id
        )
        ORDER BY p.id, a.id, u.id
    """))
    op.execute(sa.text("""
        UPDATE ajustes_razonables aj
        SET asignatura_id = pa.asignatura_id
        FROM piar_asignaturas pa
        WHERE aj.piar_id = pa.piar_id
          AND aj.asignatura_id IS NULL
          AND LOWER(BTRIM(aj.area)) = LOWER(BTRIM(pa.nombre_asignatura))
    """))

    if not _has_table("piar_versiones"):
        op.create_table(
            "piar_versiones",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("numero", sa.Integer(), nullable=False),
            sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("pdf_archivo", sa.LargeBinary(), nullable=False),
            sa.Column("sha256", sa.Text(), nullable=False),
            sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("numero > 0", name="ck_piar_version_numero"),
            sa.ForeignKeyConstraint(["creado_por"], ["usuarios.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("piar_id", "numero", name="uq_piar_version_numero"),
        )
    if not _has_index("piar_versiones", "piar_versiones_piar_id_idx"):
        op.create_index("piar_versiones_piar_id_idx", "piar_versiones", ["piar_id"])


def downgrade() -> None:
    op.drop_index("piar_versiones_piar_id_idx", table_name="piar_versiones")
    op.drop_table("piar_versiones")
    op.drop_index("piar_asignaturas_piar_id_idx", table_name="piar_asignaturas")
    op.drop_table("piar_asignaturas")
    op.drop_index("piar_participantes_piar_id_idx", table_name="piar_participantes")
    op.drop_table("piar_participantes")
    op.drop_constraint("fk_ajustes_asignatura", "ajustes_razonables", type_="foreignkey")
    op.drop_column("ajustes_razonables", "asignatura_id")
    op.drop_column("caracteristicas_estudiante", "otras_observaciones")
    op.drop_column("caracteristicas_estudiante", "entorno_familiar_social_economico")
    op.drop_constraint("uq_piars_estudiante_anio", "piars", type_="unique")
    op.drop_column("piars", "version_actual")
    op.drop_column("piars", "lugar_diligenciamiento")
    op.drop_constraint("ck_trayectorias_estado_ultimo_grado", "trayectorias_educativas", type_="check")
    op.drop_column("trayectorias_educativas", "estado_ultimo_grado")
    op.drop_column("trayectorias_educativas", "vinculado_sistema_anterior")
    op.drop_column("estudiantes", "pertenece_grupo_etnico")
    op.alter_column("estudiantes", "registro_victima", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("estudiantes", "victima_conflicto", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("estudiantes", "en_centro_proteccion", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("estudiantes", "barrio_vereda", existing_type=sa.Text(), nullable=False)
    op.alter_column("estudiantes", "direccion", existing_type=sa.Text(), nullable=False)
    op.alter_column("estudiantes", "municipio_residencia", existing_type=sa.Text(), nullable=False)
    op.alter_column("estudiantes", "departamento_residencia", existing_type=sa.Text(), nullable=False)
