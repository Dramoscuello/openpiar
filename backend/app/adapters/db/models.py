# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Modelos ORM de SQLAlchemy para OpenPiar.

IMPORTANTE: Estos modelos son ADAPTADORES, no entidades de dominio.
Viven en la capa de infraestructura. Las entidades puras del dominio
están en app/domain/entities/ y no tienen dependencias de SQLAlchemy.

Los repositorios mapean entre estos modelos ORM y las entidades de dominio.

Tablas definidas según: architecture_roadmap.md — Sección 2
"""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    Table,
    Column,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.adapters.db.session import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tabla 1: configuracion_sistema
# Singleton — una sola fila por instancia de OpenPiar
# ---------------------------------------------------------------------------

class ConfiguracionSistemaORM(Base):
    __tablename__ = "configuracion_sistema"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre_institucion: Mapped[str] = mapped_column(Text, nullable=False)
    nit: Mapped[str] = mapped_column(Text, nullable=False)
    codigo_dane: Mapped[str] = mapped_column(Text, nullable=False)
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    telefono_contacto: Mapped[Optional[str]] = mapped_column(Text)
    correo_contacto: Mapped[Optional[str]] = mapped_column(Text)
    nombre_rector: Mapped[Optional[str]] = mapped_column(Text)
    gemini_api_key: Mapped[Optional[str]] = mapped_column(Text)  # Encriptada en reposo
    contexto_institucion: Mapped[Optional[str]] = mapped_column(Text)
    pei_nombre_archivo: Mapped[Optional[str]] = mapped_column(Text)
    pei_modelo_pedagogico: Mapped[Optional[str]] = mapped_column(Text)
    pei_valores_principios: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    setup_completado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "configuracion_sistema_pei_valores_gin",
            pei_valores_principios,
            postgresql_using="gin",
        ),
    )


# ---------------------------------------------------------------------------
# Tabla 2: periodos_academicos
# ---------------------------------------------------------------------------

class PeriodoAcademicoORM(Base):
    __tablename__ = "periodos_academicos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Tabla 3: usuarios
# ---------------------------------------------------------------------------

class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    apellido: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(Text, nullable=False)
    cargo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tour_completado: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    # Relaciones
    estudiantes: Mapped[list["EstudianteORM"]] = relationship(
        back_populates="creador", foreign_keys="EstudianteORM.creado_por"
    )
    sedes: Mapped[list["SedeORM"]] = relationship(
        "SedeORM", secondary="docente_sedes", back_populates="docentes"
    )
    grupos_dirigidos: Mapped[list["GrupoORM"]] = relationship(
        "GrupoORM", back_populates="director"
    )
    carga_academica: Mapped[list["CargaAcademicaORM"]] = relationship(
        "CargaAcademicaORM", back_populates="docente"
    )
    ajustes_creados: Mapped[list["AjusteRazonableORM"]] = relationship(
        "AjusteRazonableORM", back_populates="creador", foreign_keys="AjusteRazonableORM.creado_por"
    )

    __table_args__ = (
        CheckConstraint(
            "rol IN ('docente_aula', 'docente_apoyo', 'orientador', 'directivo')",
            name="ck_usuarios_rol",
        ),
        CheckConstraint("length(email) <= 255", name="ck_usuarios_email_len"),
        Index("usuarios_email_lower_idx", func.lower(email)),
    )


# ---------------------------------------------------------------------------
# Tabla 3: estudiantes (Anexo 1 — Información general)
# ---------------------------------------------------------------------------

class EstudianteORM(Base):
    __tablename__ = "estudiantes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    nombres: Mapped[str] = mapped_column(Text, nullable=False)
    apellidos: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_documento: Mapped[str] = mapped_column(Text, nullable=False)
    numero_documento: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    edad: Mapped[int] = mapped_column(Integer, nullable=False)
    lugar_nacimiento: Mapped[Optional[str]] = mapped_column(Text)
    departamento_residencia: Mapped[str] = mapped_column(Text, nullable=False)
    municipio_residencia: Mapped[str] = mapped_column(Text, nullable=False)
    direccion: Mapped[str] = mapped_column(Text, nullable=False)
    barrio_vereda: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(Text)
    correo: Mapped[Optional[str]] = mapped_column(Text)
    en_centro_proteccion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    centro_proteccion_donde: Mapped[Optional[str]] = mapped_column(Text)
    grupo_etnico: Mapped[Optional[str]] = mapped_column(Text)
    victima_conflicto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registro_victima: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    grupo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grupos.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    # Relaciones
    creador: Mapped[Optional["UsuarioORM"]] = relationship(
        back_populates="estudiantes", foreign_keys=[creado_por]
    )
    grupo: Mapped[Optional["GrupoORM"]] = relationship()
    entorno_salud: Mapped[Optional["EntornoSaludORM"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )
    entorno_hogar: Mapped[Optional["EntornoHogarORM"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )
    trayectoria_educativa: Mapped[Optional["TrayectoriaEducativaORM"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )
    matricula_actual: Mapped[Optional["MatriculaActualORM"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )
    piars: Mapped[list["PiarORM"]] = relationship(
        back_populates="estudiante", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "tipo_documento IN ('TI', 'CC', 'RC', 'NES', 'PEP')",
            name="ck_estudiantes_tipo_doc",
        ),
        CheckConstraint("length(numero_documento) <= 50", name="ck_estudiantes_num_doc_len"),
        CheckConstraint("edad >= 0", name="ck_estudiantes_edad"),
        Index("estudiantes_creado_por_idx", creado_por),
    )


# ---------------------------------------------------------------------------
# Tabla 4: entornos_salud (Anexo 1 — Salud)
# ---------------------------------------------------------------------------

class EntornoSaludORM(Base):
    __tablename__ = "entornos_salud"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiantes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    afiliacion_salud: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eps: Mapped[Optional[str]] = mapped_column(Text)
    regimen: Mapped[Optional[str]] = mapped_column(Text)
    lugar_emergencias: Mapped[Optional[str]] = mapped_column(Text)
    atendido_sector_salud: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frecuencia_atencion_salud: Mapped[Optional[str]] = mapped_column(Text)
    tiene_diagnostico_medico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    diagnostico_medico: Mapped[Optional[str]] = mapped_column(Text)
    asiste_terapias: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    terapias_detalle: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    tratamiento_medico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tratamiento_medico_cual: Mapped[Optional[str]] = mapped_column(Text)
    consume_medicamentos: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    medicamentos_detalle: Mapped[Optional[str]] = mapped_column(Text)
    productos_apoyo_movilidad: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    productos_apoyo_cual: Mapped[Optional[str]] = mapped_column(Text)
    soporte_medico_nombre: Mapped[Optional[str]] = mapped_column(Text)
    soporte_medico_archivo: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    estudiante: Mapped["EstudianteORM"] = relationship(back_populates="entorno_salud")

    __table_args__ = (
        CheckConstraint(
            "regimen IN ('contributivo', 'subsidiado') OR regimen IS NULL",
            name="ck_entornos_salud_regimen",
        ),
        Index(
            "entornos_salud_terapias_detalle_gin",
            terapias_detalle,
            postgresql_using="gin",
        ),
    )


# ---------------------------------------------------------------------------
# Tabla 5: entornos_hogar (Anexo 1 — Hogar y Cuidador)
# ---------------------------------------------------------------------------

class EntornoHogarORM(Base):
    __tablename__ = "entornos_hogar"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiantes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    nombre_madre: Mapped[Optional[str]] = mapped_column(Text)
    ocupacion_madre: Mapped[Optional[str]] = mapped_column(Text)
    nivel_educativo_madre: Mapped[Optional[str]] = mapped_column(Text)
    telefono_madre: Mapped[Optional[str]] = mapped_column(Text)
    correo_madre: Mapped[Optional[str]] = mapped_column(Text)
    numero_documento_madre: Mapped[Optional[str]] = mapped_column(Text, index=True)
    nombre_padre: Mapped[Optional[str]] = mapped_column(Text)
    ocupacion_padre: Mapped[Optional[str]] = mapped_column(Text)
    nivel_educativo_padre: Mapped[Optional[str]] = mapped_column(Text)
    telefono_padre: Mapped[Optional[str]] = mapped_column(Text)
    correo_padre: Mapped[Optional[str]] = mapped_column(Text)
    numero_documento_padre: Mapped[Optional[str]] = mapped_column(Text, index=True)
    nombre_cuidador: Mapped[Optional[str]] = mapped_column(Text)
    parentesco_cuidador: Mapped[Optional[str]] = mapped_column(Text)
    nivel_educativo_cuidador: Mapped[Optional[str]] = mapped_column(Text)
    telefono_cuidador: Mapped[Optional[str]] = mapped_column(Text)
    correo_cuidador: Mapped[Optional[str]] = mapped_column(Text)
    acudiente_principal: Mapped[Optional[str]] = mapped_column(Text)
    personas_vive_estudiante: Mapped[Optional[str]] = mapped_column(Text)
    numero_hermanos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lugar_que_ocupa: Mapped[Optional[int]] = mapped_column(Integer)
    apoyo_crianza: Mapped[Optional[str]] = mapped_column(Text)
    bajo_proteccion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recibe_subsidio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subsidio_cual: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    estudiante: Mapped["EstudianteORM"] = relationship(back_populates="entorno_hogar")

    __table_args__ = (
        CheckConstraint("numero_hermanos >= 0", name="ck_entornos_hogar_hermanos"),
        CheckConstraint(
            "lugar_que_ocupa > 0 OR lugar_que_ocupa IS NULL",
            name="ck_entornos_hogar_lugar",
        ),
        CheckConstraint(
            "acudiente_principal IN ('madre', 'padre', 'cuidador') OR acudiente_principal IS NULL",
            name="ck_entornos_hogar_acudiente",
        ),
    )


# ---------------------------------------------------------------------------
# Tabla 6: trayectorias_educativas (Anexo 1 — Trayectoria)
# ---------------------------------------------------------------------------

class TrayectoriaEducativaORM(Base):
    __tablename__ = "trayectorias_educativas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiantes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    vinculado_educacion_inicial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    educacion_inicial_instituciones: Mapped[Optional[str]] = mapped_column(Text)
    ultimo_grado_cursado: Mapped[Optional[str]] = mapped_column(Text)
    aprobo_ultimo_grado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observaciones_trayectoria: Mapped[Optional[str]] = mapped_column(Text)
    recibe_informe_pedagogico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    institucion_procedencia_informe: Mapped[Optional[str]] = mapped_column(Text)
    asiste_programas_complementarios: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    programas_complementarios_cuales: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    estudiante: Mapped["EstudianteORM"] = relationship(back_populates="trayectoria_educativa")


# ---------------------------------------------------------------------------
# Tabla 7: matriculas_actuales (Anexo 1 — Colegio actual)
# ---------------------------------------------------------------------------

class MatriculaActualORM(Base):
    __tablename__ = "matriculas_actuales"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiantes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    institucion_educativa: Mapped[str] = mapped_column(Text, nullable=False)
    sede: Mapped[str] = mapped_column(Text, nullable=False)
    grado_ingreso: Mapped[str] = mapped_column(Text, nullable=False)
    jornada: Mapped[str] = mapped_column(Text, nullable=False)
    medio_transporte: Mapped[Optional[str]] = mapped_column(Text)
    distancia_tiempo_hogar: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    estudiante: Mapped["EstudianteORM"] = relationship(back_populates="matricula_actual")

    __table_args__ = (
        CheckConstraint(
            "jornada IN ('mañana', 'tarde', 'unica', 'nocturna')",
            name="ck_matriculas_jornada",
        ),
    )


# ---------------------------------------------------------------------------
# Tabla 8: piars (Anexo 2 — Control del PIAR)
# ---------------------------------------------------------------------------

class PiarORM(Base):
    __tablename__ = "piars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    estudiante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("estudiantes.id", ondelete="CASCADE"),
        nullable=False,
    )
    anio_lectivo: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_creacion: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="borrador")
    creado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    docentes_elaboran: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    # Relaciones
    estudiante: Mapped["EstudianteORM"] = relationship(back_populates="piars")
    caracteristicas: Mapped[Optional["CaracteristicasEstudianteORM"]] = relationship(
        back_populates="piar", cascade="all, delete-orphan"
    )
    ajustes_razonables: Mapped[list["AjusteRazonableORM"]] = relationship(
        back_populates="piar", cascade="all, delete-orphan"
    )
    recomendaciones_pmi: Mapped[list["RecomendacionPMIORM"]] = relationship(
        back_populates="piar", cascade="all, delete-orphan"
    )
    acta_acuerdo: Mapped[Optional["ActaAcuerdoORM"]] = relationship(
        back_populates="piar", cascade="all, delete-orphan"
    )
    auditoria_entradas: Mapped[list["AuditoriaCambioORM"]] = relationship(
        back_populates="piar", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('borrador', 'generando_ia', 'en_revision', 'firmado')",
            name="ck_piars_estado",
        ),
        CheckConstraint("anio_lectivo >= 2020", name="ck_piars_anio"),
        Index("piars_estudiante_id_idx", estudiante_id),
        Index("piars_creado_por_idx", creado_por),
    )


# ---------------------------------------------------------------------------
# Tabla 9: caracteristicas_estudiante (Anexo 2 — Sección 1)
# ---------------------------------------------------------------------------

class CaracteristicasEstudianteORM(Base):
    __tablename__ = "caracteristicas_estudiante"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    descripcion_gustos_intereses: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion_habilidades: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    piar: Mapped["PiarORM"] = relationship(back_populates="caracteristicas")


# ---------------------------------------------------------------------------
# Tabla 10: ajustes_razonables (Anexo 2 — Matriz de ajustes por trimestre)
# ---------------------------------------------------------------------------

class AjusteRazonableORM(Base):
    __tablename__ = "ajustes_razonables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        nullable=False,
    )
    periodo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("periodos_academicos.id", ondelete="CASCADE"),
        nullable=False,
    )
    creado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    area: Mapped[str] = mapped_column(Text, nullable=False)
    titulo_tema: Mapped[Optional[str]] = mapped_column(Text)
    objetivos_propositos: Mapped[str] = mapped_column(Text, nullable=False)
    barreras_evidenciadas: Mapped[str] = mapped_column(Text, nullable=False)
    ajustes_estrategias: Mapped[str] = mapped_column(Text, nullable=False)
    evaluacion_ajustes: Mapped[Optional[str]] = mapped_column(Text)
    puntuacion: Mapped[Optional[int]] = mapped_column(
        Integer, CheckConstraint("puntuacion BETWEEN 1 AND 5", name="ck_ajustes_puntuacion"), nullable=True
    )
    comentario_puntuacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    creador: Mapped[Optional["UsuarioORM"]] = relationship(
        back_populates="ajustes_creados", foreign_keys=[creado_por]
    )
    piar: Mapped["PiarORM"] = relationship(back_populates="ajustes_razonables")
    periodo: Mapped["PeriodoAcademicoORM"] = relationship()
    evidencias: Mapped[list["EvidenciaAjusteORM"]] = relationship(
        back_populates="ajuste_razonable", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ajustes_razonables_piar_id_idx", piar_id),
        Index("ajustes_razonables_creado_por_idx", creado_por),
    )


# ---------------------------------------------------------------------------
# Tabla 11: recomendaciones_pmi (Anexo 2 — Sección 7 PMI)
# ---------------------------------------------------------------------------

class RecomendacionPMIORM(Base):
    __tablename__ = "recomendaciones_pmi"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    acciones: Mapped[str] = mapped_column(Text, nullable=False)
    estrategias_implementar: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    piar: Mapped["PiarORM"] = relationship(back_populates="recomendaciones_pmi")

    __table_args__ = (
        CheckConstraint(
            "actor IN ('Familia', 'Docentes', 'Directivos', 'Administrativos', 'Pares')",
            name="ck_recomendaciones_actor",
        ),
        Index("recomendaciones_pmi_piar_id_idx", piar_id),
    )


# ---------------------------------------------------------------------------
# Tabla 12: actas_acuerdo (Anexo 3 — Acta legal)
# ---------------------------------------------------------------------------

class ActaAcuerdoORM(Base):
    __tablename__ = "actas_acuerdo"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    fecha_firma: Mapped[Optional[date]] = mapped_column(Date)
    compromisos_aula: Mapped[Optional[str]] = mapped_column(Text)
    firmado_estudiante: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firmado_acudiente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firmado_docente_apoyo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firmado_docentes_aula: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firmado_directivo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    piar: Mapped["PiarORM"] = relationship(back_populates="acta_acuerdo")
    compromisos_casa: Mapped[list["CompromisoCasaORM"]] = relationship(
        back_populates="acta", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# Tabla 13: compromisos_casa (Anexo 3 — Apoyo familiar en casa)
# ---------------------------------------------------------------------------

class CompromisoCasaORM(Base):
    __tablename__ = "compromisos_casa"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    acta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actas_acuerdo.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre_actividad: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion_estrategia: Mapped[str] = mapped_column(Text, nullable=False)
    frecuencia: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    acta: Mapped["ActaAcuerdoORM"] = relationship(back_populates="compromisos_casa")

    __table_args__ = (
        CheckConstraint(
            "frecuencia IN ('diaria', 'semanal', 'permanente')",
            name="ck_compromisos_frecuencia",
        ),
        Index("compromisos_casa_acta_id_idx", acta_id),
    )


# ---------------------------------------------------------------------------
# Tabla: auditoria_cambios
# Historial de cambios en entidades del PIAR
# ---------------------------------------------------------------------------

class AuditoriaCambioORM(Base):
    __tablename__ = "auditoria_cambios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    entidad_tipo: Mapped[str] = mapped_column(Text, nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        nullable=False,
    )
    accion: Mapped[str] = mapped_column(Text, nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    datos_anteriores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    datos_nuevos: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        default=_now, server_default=func.now()
    )
    ip_origen: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    usuario: Mapped[Optional["UsuarioORM"]] = relationship()
    piar: Mapped["PiarORM"] = relationship(back_populates="auditoria_entradas")

    __table_args__ = (
        CheckConstraint(
            "entidad_tipo IN ("
            "'ajuste_razonable', 'recomendacion_pmi', 'acta_acuerdo', "
            "'caracteristicas_estudiante', 'compromiso_casa', 'piar_estado', 'evidencia_ajuste'"
            ")",
            name="ck_auditoria_entidad_tipo",
        ),
        CheckConstraint(
            "accion IN ('crear', 'modificar', 'eliminar')",
            name="ck_auditoria_accion",
        ),
        Index("auditoria_cambios_piar_id_idx", piar_id),
        Index("auditoria_cambios_fecha_idx", fecha.desc()),
    )


# ---------------------------------------------------------------------------
# Tabla 14: derechos_dba (Currículum MEN — Derechos Básicos de Aprendizaje)
# ---------------------------------------------------------------------------

class DerechoDBAORM(Base):
    __tablename__ = "derechos_dba"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    grado: Mapped[str] = mapped_column(Text, nullable=False)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)
    evidencias: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    ejemplos: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("derechos_dba_busqueda_idx", "grado", "area"),
        Index(
            "derechos_dba_evidencias_gin",
            evidencias,
            postgresql_using="gin",
        ),
    )


# ---------------------------------------------------------------------------
# Tabla 15: estandares_ebc (Currículum MEN — Estándares Básicos de Competencia)
# ---------------------------------------------------------------------------

class EstandarEBCORM(Base):
    __tablename__ = "estandares_ebc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rango_grados: Mapped[str] = mapped_column(Text, nullable=False)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    factor: Mapped[str] = mapped_column(Text, nullable=False)
    enunciado: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("estandares_ebc_busqueda_idx", "rango_grados", "area"),
    )


# ---------------------------------------------------------------------------
# Nuevas Tablas de Control Institucional y Carga Académica (Sedes, Asignaturas, Grupos, Docentes)
# ---------------------------------------------------------------------------

docente_sedes = Table(
    "docente_sedes",
    Base.metadata,
    Column("docente_id", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True),
    Column("sede_id", UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="CASCADE"), primary_key=True)
)


class SedeORM(Base):
    __tablename__ = "sedes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(Text)
    telefono: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now, server_default=func.now())

    docentes: Mapped[list["UsuarioORM"]] = relationship(
        "UsuarioORM", secondary=docente_sedes, back_populates="sedes"
    )
    grupos: Mapped[list["GrupoORM"]] = relationship(
        "GrupoORM", back_populates="sede", cascade="all, delete-orphan"
    )


class AreaORM(Base):
    __tablename__ = "areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    institucion_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("configuracion_sistema.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    # Relaciones
    asignaturas: Mapped[list["AsignaturaORM"]] = relationship(
        "AsignaturaORM", back_populates="area", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("nombre", "institucion_id", name="uq_area_nombre_institucion"),
    )


class AsignaturaORM(Base):
    __tablename__ = "asignaturas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    # Relaciones
    area: Mapped["AreaORM"] = relationship(back_populates="asignaturas")

    @property
    def area_nombre(self) -> str:
        return self.area.nombre if self.area else ""

    __table_args__ = (
        UniqueConstraint("nombre", "area_id", name="uq_asignatura_nombre_area"),
    )


class GradoORM(Base):
    __tablename__ = "grados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    institucion_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("configuracion_sistema.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    # Relaciones
    grupos: Mapped[list["GrupoORM"]] = relationship(
        "GrupoORM", back_populates="grado", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("nombre", "institucion_id", name="uq_grado_nombre_institucion"),
    )


class GrupoORM(Base):
    __tablename__ = "grupos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    grado_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grados.id", ondelete="CASCADE"), nullable=False)
    sede_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="CASCADE"), nullable=False)
    director_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now, server_default=func.now())

    sede: Mapped["SedeORM"] = relationship(back_populates="grupos")
    director: Mapped[Optional["UsuarioORM"]] = relationship(back_populates="grupos_dirigidos")
    carga: Mapped[list["CargaAcademicaORM"]] = relationship(back_populates="grupo", cascade="all, delete-orphan")
    grado: Mapped["GradoORM"] = relationship(back_populates="grupos")

    __table_args__ = (
        UniqueConstraint("nombre", "grado_id", "sede_id", name="uq_grupo_sede"),
    )


class CargaAcademicaORM(Base):
    __tablename__ = "carga_academica"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    docente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    asignatura_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("asignaturas.id", ondelete="CASCADE"), nullable=False)
    grupo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("grupos.id", ondelete="CASCADE"), nullable=False)

    docente: Mapped["UsuarioORM"] = relationship(back_populates="carga_academica")
    asignatura: Mapped["AsignaturaORM"] = relationship()
    grupo: Mapped["GrupoORM"] = relationship(back_populates="carga")

    __table_args__ = (
        UniqueConstraint("docente_id", "asignatura_id", "grupo_id", name="uq_carga_academica"),
    )


# ---------------------------------------------------------------------------
# Tabla: evidencias_ajuste
# Portafolio de evidencias vinculadas a ajustes DUA
# ---------------------------------------------------------------------------

class EvidenciaAjusteORM(Base):
    __tablename__ = "evidencias_ajuste"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_uuid_pk
    )
    ajuste_razonable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ajustes_razonables.id", ondelete="CASCADE"),
        nullable=False,
    )
    piar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("piars.id", ondelete="CASCADE"),
        nullable=False,
    )
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    creado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    fecha_subida: Mapped[datetime] = mapped_column(
        default=_now, server_default=func.now()
    )

    ajuste_razonable: Mapped["AjusteRazonableORM"] = relationship(
        back_populates="evidencias"
    )
    piar: Mapped["PiarORM"] = relationship()
    creador: Mapped[Optional["UsuarioORM"]] = relationship()

    __table_args__ = (
        CheckConstraint(
            "tipo_archivo IN ('imagen', 'pdf')",
            name="ck_evidencias_tipo_archivo",
        ),
        Index("evidencias_ajuste_ajuste_id_idx", ajuste_razonable_id),
        Index("evidencias_ajuste_piar_id_idx", piar_id),
    )
