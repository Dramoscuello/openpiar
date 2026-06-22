# initial_schema_all_tables — OpenPiar
# Revision ID: 6e0dfd5da743
# Revises: (primera migración)
# Create Date: 2026-06-22
#
# Crea todas las tablas del schema OpenPiar definidas en architecture_roadmap.md:
# 1. configuracion_sistema    6. trayectorias_educativas   11. recomendaciones_pmi
# 2. usuarios                 7. matriculas_actuales       12. actas_acuerdo
# 3. estudiantes              8. piars                     13. compromisos_casa
# 4. entornos_salud           9. caracteristicas_estudiante 14. derechos_dba
# 5. entornos_hogar          10. ajustes_razonables        15. estandares_ebc

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6e0dfd5da743"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. configuracion_sistema (Singleton — datos del colegio)
    # -----------------------------------------------------------------------
    op.create_table(
        "configuracion_sistema",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre_institucion", sa.Text(), nullable=False),
        sa.Column("nit", sa.Text(), nullable=False),
        sa.Column("codigo_dane", sa.Text(), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=False),
        sa.Column("telefono_contacto", sa.Text(), nullable=True),
        sa.Column("correo_contacto", sa.Text(), nullable=True),
        sa.Column("nombre_rector", sa.Text(), nullable=True),
        sa.Column("gemini_api_key", sa.Text(), nullable=True),
        sa.Column("pei_nombre_archivo", sa.Text(), nullable=True),
        sa.Column("pei_modelo_pedagogico", sa.Text(), nullable=True),
        sa.Column(
            "pei_valores_principios",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("setup_completado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "configuracion_sistema_pei_valores_gin",
        "configuracion_sistema",
        ["pei_valores_principios"],
        postgresql_using="gin",
    )

    # -----------------------------------------------------------------------
    # 2. usuarios
    # -----------------------------------------------------------------------
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("apellido", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("cargo", sa.Text(), nullable=True),
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
            "rol IN ('docente_aula', 'docente_apoyo', 'orientador', 'directivo')",
            name="ck_usuarios_rol",
        ),
        sa.CheckConstraint(
            "cargo IS NULL OR cargo IN ('Rector', 'Coordinador', 'Docente encargado')",
            name="ck_usuarios_cargo",
        ),
        sa.CheckConstraint("length(email) <= 255", name="ck_usuarios_email_len"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "usuarios_email_lower_idx",
        "usuarios",
        [sa.text("lower(email)")],
    )

    # -----------------------------------------------------------------------
    # 3. estudiantes (Anexo 1 — Información General)
    # -----------------------------------------------------------------------
    op.create_table(
        "estudiantes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombres", sa.Text(), nullable=False),
        sa.Column("apellidos", sa.Text(), nullable=False),
        sa.Column("tipo_documento", sa.Text(), nullable=False),
        sa.Column("numero_documento", sa.Text(), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=False),
        sa.Column("edad", sa.Integer(), nullable=False),
        sa.Column("lugar_nacimiento", sa.Text(), nullable=True),
        sa.Column("departamento_residencia", sa.Text(), nullable=False),
        sa.Column("municipio_residencia", sa.Text(), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=False),
        sa.Column("barrio_vereda", sa.Text(), nullable=False),
        sa.Column("telefono", sa.Text(), nullable=True),
        sa.Column("correo", sa.Text(), nullable=True),
        sa.Column("en_centro_proteccion", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("centro_proteccion_donde", sa.Text(), nullable=True),
        sa.Column("grupo_etnico", sa.Text(), nullable=True),
        sa.Column("victima_conflicto", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("registro_victima", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
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
            "tipo_documento IN ('TI', 'CC', 'RC', 'NES', 'PEP')",
            name="ck_estudiantes_tipo_doc",
        ),
        sa.CheckConstraint("length(numero_documento) <= 50", name="ck_estudiantes_num_doc_len"),
        sa.CheckConstraint("edad >= 0", name="ck_estudiantes_edad"),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_documento"),
    )
    op.create_index("estudiantes_creado_por_idx", "estudiantes", ["creado_por"])

    # -----------------------------------------------------------------------
    # 4. entornos_salud (Anexo 1 — Salud)
    # -----------------------------------------------------------------------
    op.create_table(
        "entornos_salud",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("afiliacion_salud", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("eps", sa.Text(), nullable=True),
        sa.Column("regimen", sa.Text(), nullable=True),
        sa.Column("lugar_emergencias", sa.Text(), nullable=True),
        sa.Column("atendido_sector_salud", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("frecuencia_atencion_salud", sa.Text(), nullable=True),
        sa.Column("tiene_diagnostico_medico", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("diagnostico_medico", sa.Text(), nullable=True),
        sa.Column("asiste_terapias", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "terapias_detalle",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("tratamiento_medico", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tratamiento_medico_cual", sa.Text(), nullable=True),
        sa.Column("consume_medicamentos", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("medicamentos_detalle", sa.Text(), nullable=True),
        sa.Column("productos_apoyo_movilidad", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("productos_apoyo_cual", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "regimen IN ('contributivo', 'subsidiado') OR regimen IS NULL",
            name="ck_entornos_salud_regimen",
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiantes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estudiante_id"),
    )
    op.create_index(
        "entornos_salud_terapias_detalle_gin",
        "entornos_salud",
        ["terapias_detalle"],
        postgresql_using="gin",
    )

    # -----------------------------------------------------------------------
    # 5. entornos_hogar (Anexo 1 — Hogar y Cuidador)
    # -----------------------------------------------------------------------
    op.create_table(
        "entornos_hogar",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre_madre", sa.Text(), nullable=True),
        sa.Column("ocupacion_madre", sa.Text(), nullable=True),
        sa.Column("nivel_educativo_madre", sa.Text(), nullable=True),
        sa.Column("nombre_padre", sa.Text(), nullable=True),
        sa.Column("ocupacion_padre", sa.Text(), nullable=True),
        sa.Column("nivel_educativo_padre", sa.Text(), nullable=True),
        sa.Column("nombre_cuidador", sa.Text(), nullable=True),
        sa.Column("parentesco_cuidador", sa.Text(), nullable=True),
        sa.Column("nivel_educativo_cuidador", sa.Text(), nullable=True),
        sa.Column("telefono_cuidador", sa.Text(), nullable=True),
        sa.Column("correo_cuidador", sa.Text(), nullable=True),
        sa.Column("personas_vive_estudiante", sa.Text(), nullable=True),
        sa.Column("numero_hermanos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lugar_que_ocupa", sa.Integer(), nullable=True),
        sa.Column("apoyo_crianza", sa.Text(), nullable=True),
        sa.Column("bajo_proteccion", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("recibe_subsidio", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("subsidio_cual", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("numero_hermanos >= 0", name="ck_entornos_hogar_hermanos"),
        sa.CheckConstraint(
            "lugar_que_ocupa > 0 OR lugar_que_ocupa IS NULL",
            name="ck_entornos_hogar_lugar",
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiantes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estudiante_id"),
    )

    # -----------------------------------------------------------------------
    # 6. trayectorias_educativas (Anexo 1 — Trayectoria)
    # -----------------------------------------------------------------------
    op.create_table(
        "trayectorias_educativas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vinculado_educacion_inicial", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("educacion_inicial_instituciones", sa.Text(), nullable=True),
        sa.Column("ultimo_grado_cursado", sa.Text(), nullable=True),
        sa.Column("aprobo_ultimo_grado", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("observaciones_trayectoria", sa.Text(), nullable=True),
        sa.Column("recibe_informe_pedagogico", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("institucion_procedencia_informe", sa.Text(), nullable=True),
        sa.Column("asiste_programas_complementarios", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("programas_complementarios_cuales", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiantes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estudiante_id"),
    )

    # -----------------------------------------------------------------------
    # 7. matriculas_actuales (Anexo 1 — Colegio Actual)
    # -----------------------------------------------------------------------
    op.create_table(
        "matriculas_actuales",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institucion_educativa", sa.Text(), nullable=False),
        sa.Column("sede", sa.Text(), nullable=False),
        sa.Column("grado_ingreso", sa.Text(), nullable=False),
        sa.Column("jornada", sa.Text(), nullable=False),
        sa.Column("medio_transporte", sa.Text(), nullable=True),
        sa.Column("distancia_tiempo_hogar", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jornada IN ('mañana', 'tarde', 'unica', 'nocturna')",
            name="ck_matriculas_jornada",
        ),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiantes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("estudiante_id"),
    )

    # -----------------------------------------------------------------------
    # 8. piars (Anexo 2 — Agregado Raíz del PIAR)
    # -----------------------------------------------------------------------
    op.create_table(
        "piars",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estudiante_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anio_lectivo", sa.Integer(), nullable=False),
        sa.Column("fecha_creacion", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("fecha_limite_firma", sa.Date(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False, server_default="borrador"),
        sa.Column("creado_por", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("docentes_elaboran", sa.Text(), nullable=True),
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
            "estado IN ('borrador', 'generando_ia', 'en_revision', 'firmado', 'vencido')",
            name="ck_piars_estado",
        ),
        sa.CheckConstraint("anio_lectivo >= 2020", name="ck_piars_anio"),
        sa.ForeignKeyConstraint(
            ["estudiante_id"], ["estudiantes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["creado_por"], ["usuarios.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("piars_estudiante_id_idx", "piars", ["estudiante_id"])
    op.create_index("piars_creado_por_idx", "piars", ["creado_por"])

    # -----------------------------------------------------------------------
    # 9. caracteristicas_estudiante (Anexo 2 — Sección 1)
    # -----------------------------------------------------------------------
    op.create_table(
        "caracteristicas_estudiante",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("descripcion_gustos_intereses", sa.Text(), nullable=False),
        sa.Column("descripcion_habilidades", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("piar_id"),
    )

    # -----------------------------------------------------------------------
    # 10. ajustes_razonables (Anexo 2 — Matriz trimestral)
    # -----------------------------------------------------------------------
    op.create_table(
        "ajustes_razonables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("objetivos_propositos", sa.Text(), nullable=False),
        sa.Column("barreras_evidenciadas", sa.Text(), nullable=False),
        sa.Column("ajustes_estrategias", sa.Text(), nullable=False),
        sa.Column("evaluacion_ajustes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("trimestre IN (1, 2, 3)", name="ck_ajustes_trimestre"),
        sa.CheckConstraint(
            "area IN ('Matemáticas', 'Ciencias', 'Lenguaje', 'Convivencia', "
            "'Socialización', 'Participación', 'Autonomía', 'Autocontrol')",
            name="ck_ajustes_area",
        ),
        sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ajustes_razonables_piar_id_idx", "ajustes_razonables", ["piar_id"])

    # -----------------------------------------------------------------------
    # 11. recomendaciones_pmi (Anexo 2 — Sección 7 PMI)
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 12. actas_acuerdo (Anexo 3 — Acta Legal)
    # -----------------------------------------------------------------------
    op.create_table(
        "actas_acuerdo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("piar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_firma", sa.Date(), nullable=True),
        sa.Column("compromisos_aula", sa.Text(), nullable=True),
        sa.Column("firmado_estudiante", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("firmado_acudiente", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("firmado_docente_apoyo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("firmado_docentes_aula", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("firmado_directivo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["piar_id"], ["piars.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("piar_id"),
    )

    # -----------------------------------------------------------------------
    # 13. compromisos_casa (Anexo 3 — Apoyo Familiar)
    # -----------------------------------------------------------------------
    op.create_table(
        "compromisos_casa",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("acta_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre_actividad", sa.Text(), nullable=False),
        sa.Column("descripcion_estrategia", sa.Text(), nullable=False),
        sa.Column("frecuencia", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "frecuencia IN ('diaria', 'semanal', 'permanente')",
            name="ck_compromisos_frecuencia",
        ),
        sa.ForeignKeyConstraint(["acta_id"], ["actas_acuerdo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("compromisos_casa_acta_id_idx", "compromisos_casa", ["acta_id"])

    # -----------------------------------------------------------------------
    # 14. derechos_dba (Currículum MEN — DBA)
    # -----------------------------------------------------------------------
    op.create_table(
        "derechos_dba",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("grado", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("enunciado", sa.Text(), nullable=False),
        sa.Column(
            "evidencias",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("ejemplos", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("derechos_dba_busqueda_idx", "derechos_dba", ["grado", "area"])
    op.create_index(
        "derechos_dba_evidencias_gin",
        "derechos_dba",
        ["evidencias"],
        postgresql_using="gin",
    )

    # -----------------------------------------------------------------------
    # 15. estandares_ebc (Currículum MEN — EBC)
    # -----------------------------------------------------------------------
    op.create_table(
        "estandares_ebc",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rango_grados", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("factor", sa.Text(), nullable=False),
        sa.Column("enunciado", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("estandares_ebc_busqueda_idx", "estandares_ebc", ["rango_grados", "area"])


def downgrade() -> None:
    # Eliminar en orden inverso a la creación (respetar FKs)
    op.drop_table("estandares_ebc")
    op.drop_table("derechos_dba")
    op.drop_table("compromisos_casa")
    op.drop_table("actas_acuerdo")
    op.drop_table("recomendaciones_pmi")
    op.drop_table("ajustes_razonables")
    op.drop_table("caracteristicas_estudiante")
    op.drop_table("piars")
    op.drop_table("matriculas_actuales")
    op.drop_table("trayectorias_educativas")
    op.drop_table("entornos_hogar")
    op.drop_table("entornos_salud")
    op.drop_table("estudiantes")
    op.drop_table("usuarios")
    op.drop_table("configuracion_sistema")

