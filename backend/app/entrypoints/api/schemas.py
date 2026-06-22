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
# Autenticación
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
