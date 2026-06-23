# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Schemas Pydantic para la API de OpenPiar.
Organizados en: Request (entrada) y Response (salida).

Estos schemas son puros DTOs de la capa HTTP — no son entidades de dominio.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseResponse(BaseModel):
    """Base para todas las respuestas — evita sobreescribir __init__."""
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Configuración del Sistema / Setup
# ---------------------------------------------------------------------------

class SetupStatusResponse(BaseResponse):
    setup_completado: bool
    nombre_institucion: Optional[str] = None
    tiene_gemini_key: bool = False


class ConfigurarSistemaRequest(BaseModel):
    """Datos del colegio + admin para el Setup Wizard (paso final)."""
    # Institución
    nombre_institucion: str = Field(..., min_length=3, max_length=500)
    nit: str = Field(..., min_length=8, max_length=20)
    codigo_dane: str = Field(..., min_length=12, max_length=12)
    direccion: str = Field(..., min_length=5)
    telefono_contacto: Optional[str] = None
    correo_contacto: Optional[EmailStr] = None
    nombre_rector: Optional[str] = None
    gemini_api_key: Optional[str] = None
    pei_nombre_archivo: Optional[str] = None
    pei_modelo_pedagogico: Optional[str] = None
    pei_valores_principios: Optional[dict] = Field(default_factory=dict)

    # Administrador inicial
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_nombre: str = Field(..., min_length=2)
    admin_apellido: str = Field(..., min_length=2)
    admin_cargo: Literal["Rector", "Coordinador", "Docente encargado"]

    @field_validator("admin_password")
    @classmethod
    def validar_admin_password(cls, v: str) -> str:
        from app.domain.entities import validar_password_fortaleza
        try:
            validar_password_fortaleza(v)
        except ValueError as exc:
            raise ValueError(str(exc))
        return v

    @field_validator("codigo_dane")
    @classmethod
    def validar_codigo_dane(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("El código DANE debe contener solo dígitos.")
        return v


class TestDBRequest(BaseModel):
    """Credenciales de PostgreSQL para probar la conexión durante el setup."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    user: str
    password: str
    database: str


class TestDBResponse(BaseResponse):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Periodos Académicos
# ---------------------------------------------------------------------------

class PeriodoAcademicoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    fecha_inicio: date
    fecha_fin: date


class PeriodoAcademicoCreate(PeriodoAcademicoBase):
    pass


class PeriodoAcademicoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None


class PeriodoAcademicoResponse(PeriodoAcademicoBase, BaseResponse):
    id: int
    activo: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validar_nueva_password(cls, v: str) -> str:
        from app.domain.entities import validar_password_fortaleza
        try:
            validar_password_fortaleza(v)
        except ValueError as exc:
            raise ValueError(str(exc))
        return v


class TokenResponse(BaseResponse):
    access_token: str
    token_type: str = "bearer"


class UsuarioResponse(BaseResponse):
    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    rol: str
    cargo: Optional[str] = None
    es_director: bool = False
    created_at: datetime


# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------

TipoDocumento = Literal["TI", "CC", "RC", "NES", "PEP"]


class CrearEstudianteRequest(BaseModel):
    """Datos mínimos para registrar un estudiante (Anexo 1 — Info General)."""
    nombres: str = Field(..., min_length=2, max_length=200)
    apellidos: str = Field(..., min_length=2, max_length=200)
    tipo_documento: TipoDocumento
    numero_documento: str = Field(..., min_length=4, max_length=50)
    fecha_nacimiento: date
    edad: int = Field(..., ge=0, le=30)
    departamento_residencia: str = Field(..., min_length=2)
    municipio_residencia: str = Field(..., min_length=2)
    direccion: str = Field(..., min_length=5)
    barrio_vereda: str = Field(..., min_length=2)
    # Opcionales
    grupo_id: Optional[uuid.UUID] = None
    lugar_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None
    en_centro_proteccion: bool = False
    centro_proteccion_donde: Optional[str] = None
    grupo_etnico: Optional[str] = None
    victima_conflicto: bool = False
    registro_victima: bool = False


class EstudianteResponse(BaseResponse):
    id: uuid.UUID
    nombres: str
    apellidos: str
    tipo_documento: str
    numero_documento: str
    fecha_nacimiento: date
    edad: int
    departamento_residencia: str
    municipio_residencia: str
    direccion: str
    barrio_vereda: str
    grupo_id: Optional[uuid.UUID] = None
    grado: Optional[str] = None
    lugar_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    en_centro_proteccion: bool
    centro_proteccion_donde: Optional[str] = None
    grupo_etnico: Optional[str] = None
    victima_conflicto: bool
    registro_victima: bool
    created_at: datetime


class EstudianteListResponse(BaseResponse):
    total: int
    items: list[EstudianteResponse]


# ---------------------------------------------------------------------------
# Entorno Salud
# ---------------------------------------------------------------------------

class EntornoSaludRequest(BaseModel):
    afiliacion_salud: bool = False
    eps: Optional[str] = None
    regimen: Optional[Literal["contributivo", "subsidiado"]] = None
    lugar_emergencias: Optional[str] = None
    atendido_sector_salud: bool = False
    frecuencia_atencion_salud: Optional[str] = None
    tiene_diagnostico_medico: bool = False
    diagnostico_medico: Optional[str] = None
    asiste_terapias: bool = False
    terapias_detalle: list[dict[str, Any]] = Field(default_factory=list)
    tratamiento_medico: bool = False
    tratamiento_medico_cual: Optional[str] = None
    consume_medicamentos: bool = False
    medicamentos_detalle: Optional[str] = None
    productos_apoyo_movilidad: bool = False
    productos_apoyo_cual: Optional[str] = None


class EntornoSaludResponse(EntornoSaludRequest, BaseResponse):
    id: uuid.UUID
    estudiante_id: uuid.UUID


# ---------------------------------------------------------------------------
# Entorno Hogar
# ---------------------------------------------------------------------------

class EntornoHogarRequest(BaseModel):
    nombre_madre: Optional[str] = None
    ocupacion_madre: Optional[str] = None
    nivel_educativo_madre: Optional[str] = None
    nombre_padre: Optional[str] = None
    ocupacion_padre: Optional[str] = None
    nivel_educativo_padre: Optional[str] = None
    nombre_cuidador: Optional[str] = None
    parentesco_cuidador: Optional[str] = None
    nivel_educativo_cuidador: Optional[str] = None
    telefono_cuidador: Optional[str] = None
    correo_cuidador: Optional[EmailStr] = None
    personas_vive_estudiante: Optional[str] = None
    numero_hermanos: int = Field(default=0, ge=0)
    lugar_que_ocupa: Optional[int] = Field(default=None, gt=0)
    apoyo_crianza: Optional[str] = None
    bajo_proteccion: bool = False
    recibe_subsidio: bool = False
    subsidio_cual: Optional[str] = None


class EntornoHogarResponse(EntornoHogarRequest, BaseResponse):
    id: uuid.UUID
    estudiante_id: uuid.UUID


# ---------------------------------------------------------------------------
# Trayectoria Educativa
# ---------------------------------------------------------------------------

class TrayectoriaEducativaRequest(BaseModel):
    vinculado_educacion_inicial: bool = False
    educacion_inicial_instituciones: Optional[str] = None
    ultimo_grado_cursado: Optional[str] = None
    aprobo_ultimo_grado: bool = True
    observaciones_trayectoria: Optional[str] = None
    recibe_informe_pedagogico: bool = False
    institucion_procedencia_informe: Optional[str] = None
    asiste_programas_complementarios: bool = False
    programas_complementarios_cuales: Optional[str] = None


class TrayectoriaEducativaResponse(TrayectoriaEducativaRequest, BaseResponse):
    id: uuid.UUID
    estudiante_id: uuid.UUID


# ---------------------------------------------------------------------------
# Matrícula Actual
# ---------------------------------------------------------------------------

class MatriculaActualRequest(BaseModel):
    institucion_educativa: str
    sede: str
    grado_ingreso: str
    jornada: Literal["mañana", "tarde", "unica", "nocturna"]
    medio_transporte: Optional[str] = None
    distancia_tiempo_hogar: Optional[str] = None


class MatriculaActualResponse(MatriculaActualRequest, BaseResponse):
    id: uuid.UUID
    estudiante_id: uuid.UUID


# ---------------------------------------------------------------------------
# Curriculum — DBA y EBC
# ---------------------------------------------------------------------------

class DBAResponse(BaseResponse):
    id: int
    grado: str
    area: str
    numero: int
    enunciado: str
    evidencias: list[str]
    ejemplos: Optional[str] = None


class EBCResponse(BaseResponse):
    id: int
    rango_grados: str
    area: str
    factor: str
    enunciado: str


class DBAListResponse(BaseResponse):
    total: int
    items: list[DBAResponse]


class EBCListResponse(BaseResponse):
    total: int
    items: list[EBCResponse]


# ---------------------------------------------------------------------------
# Anexo 2: PIAR y Ajustes Razonables
# ---------------------------------------------------------------------------

class CaracteristicasEstudianteCreate(BaseModel):
    descripcion_gustos_intereses: str = Field(..., min_length=2)
    descripcion_habilidades: str = Field(..., min_length=2)

class CaracteristicasEstudianteResponse(CaracteristicasEstudianteCreate, BaseResponse):
    id: uuid.UUID
    piar_id: uuid.UUID

class AjusteRazonableCreate(BaseModel):
    area: str = Field(..., min_length=2)
    objetivos_propositos: str = Field(..., min_length=2)
    barreras_evidenciadas: str = Field(..., min_length=2)
    ajustes_estrategias: str = Field(..., min_length=2)
    evaluacion_ajustes: Optional[str] = None

class AjusteRazonableResponse(AjusteRazonableCreate, BaseResponse):
    id: uuid.UUID
    piar_id: uuid.UUID
    periodo_id: int

class RecomendacionPMICreate(BaseModel):
    actor: Literal['Familia', 'Docentes', 'Directivos', 'Administrativos', 'Pares']
    acciones: str = Field(..., min_length=2)
    estrategias_implementar: str = Field(..., min_length=2)

class RecomendacionPMIResponse(RecomendacionPMICreate, BaseResponse):
    id: uuid.UUID
    piar_id: uuid.UUID

class PiarCreate(BaseModel):
    estudiante_id: uuid.UUID
    anio_lectivo: int = Field(..., ge=2020)
    estado: Literal['borrador', 'generando_ia', 'en_revision', 'firmado', 'vencido'] = 'borrador'
    docentes_elaboran: Optional[str] = None

class PiarUpdate(BaseModel):
    estado: Optional[Literal['borrador', 'generando_ia', 'en_revision', 'firmado', 'vencido']] = None
    docentes_elaboran: Optional[str] = None
    caracteristicas: Optional[CaracteristicasEstudianteCreate] = None

class PiarResponse(PiarCreate, BaseResponse):
    id: uuid.UUID
    fecha_creacion: date
    fecha_limite_firma: Optional[date] = None
    creado_por: Optional[uuid.UUID] = None
    caracteristicas: Optional[CaracteristicasEstudianteResponse] = None
    ajustes_razonables: list[AjusteRazonableResponse] = []
    recomendaciones_pmi: list[RecomendacionPMIResponse] = []

class GenerarAjustesRequest(BaseModel):
    barreras_evidenciadas: str
    objetivos_propositos: str
    area: str
    instrucciones_adicionales: Optional[str] = None
