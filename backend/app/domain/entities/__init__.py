# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Entidades de dominio de OpenPiar.

Las entidades tienen identidad y ciclo de vida. Son PURAS: sin imports de
SQLAlchemy, FastAPI ni ningún framework. Solo Python stdlib y value objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from app.domain.value_objects import Email, Rol


# ---------------------------------------------------------------------------
# Enums compartidos
# ---------------------------------------------------------------------------

ENTIDADES_AUDITABLES = {
    "ajuste_razonable",
    "recomendacion_pmi",
    "acta_acuerdo",
    "caracteristicas_estudiante",
    "compromiso_casa",
    "piar_estado",
    "evidencia_ajuste",
}

ACCIONES_AUDITORIA = {"crear", "modificar", "eliminar"}


# ---------------------------------------------------------------------------
# Entidad: Usuario
# ---------------------------------------------------------------------------

CARGOS_VALIDOS: set[str] = {"Rector", "Coordinador", "Docente encargado"}


def validar_password_fortaleza(password: str) -> None:
    """
    Valida que la contraseña cumpla con los requisitos mínimos de seguridad:
    - Al menos 8 caracteres de longitud.
    - Contiene letras y números.
    - Contiene al menos un carácter especial (no alfanumérico).
    """
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not any(c.isalpha() for c in password):
        raise ValueError("La contraseña debe contener al menos una letra.")
    if not any(c.isdigit() for c in password):
        raise ValueError("La contraseña debe contener al menos un número.")
    if not any(not c.isalnum() for c in password):
        raise ValueError("La contraseña debe contener al menos un carácter especial.")


@dataclass
class Usuario:
    """
    Actor del sistema educativo que puede acceder a OpenPiar.

    Roles posibles: docente_aula, docente_apoyo, orientador, directivo.
    El primer usuario creado durante el Setup Wizard es el administrador.
    """
    id: uuid.UUID
    email: Email
    password_hash: str
    nombre: str
    apellido: str
    rol: Rol
    cargo: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def crear(
        cls,
        email: str,
        password_hash: str,
        nombre: str,
        apellido: str,
        rol: str,
        cargo: Optional[str] = None,
    ) -> "Usuario":
        """Factory method — valida y crea un nuevo Usuario."""
        if cargo is not None and cargo not in CARGOS_VALIDOS:
            from app.core.exceptions import ValorObjetoInvalidoError
            raise ValorObjetoInvalidoError(
                f"Cargo '{cargo}' inválido. Cargos permitidos: {', '.join(CARGOS_VALIDOS)}"
            )

        return cls(
            id=uuid.uuid4(),
            email=Email(email),
            password_hash=password_hash,
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            rol=Rol(rol),
            cargo=cargo,
        )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"


# ---------------------------------------------------------------------------
# Entidad: Estudiante
# ---------------------------------------------------------------------------

@dataclass
class Estudiante:
    """
    Estudiante con discapacidad o TEAp beneficiario del PIAR.
    Entidad raíz del agregado de valoración pedagógica (Anexo 1).
    """
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
    # Opcionales
    lugar_nacimiento: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    en_centro_proteccion: bool = False
    centro_proteccion_donde: Optional[str] = None
    grupo_etnico: Optional[str] = None
    victima_conflicto: bool = False
    registro_victima: bool = False
    creado_por: Optional[uuid.UUID] = None
    grupo_id: Optional[uuid.UUID] = None
    codigo_acceso_familia: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def crear(
        cls,
        nombres: str,
        apellidos: str,
        tipo_documento: str,
        numero_documento: str,
        fecha_nacimiento: date,
        edad: int,
        departamento_residencia: str,
        municipio_residencia: str,
        direccion: str,
        barrio_vereda: str,
        creado_por: Optional[uuid.UUID] = None,
        grupo_id: Optional[uuid.UUID] = None,
        **kwargs,
    ) -> "Estudiante":
        """Factory method — crea un nuevo Estudiante validando invariantes básicos."""
        if edad < 0:
            raise ValueError("La edad no puede ser negativa.")
        if tipo_documento not in {"TI", "CC", "RC", "NES", "PEP"}:
            raise ValueError(f"Tipo de documento '{tipo_documento}' inválido.")

        return cls(
            id=uuid.uuid4(),
            nombres=nombres.strip(),
            apellidos=apellidos.strip(),
            tipo_documento=tipo_documento,
            numero_documento=numero_documento.strip(),
            fecha_nacimiento=fecha_nacimiento,
            edad=edad,
            departamento_residencia=departamento_residencia,
            municipio_residencia=municipio_residencia,
            direccion=direccion,
            barrio_vereda=barrio_vereda,
            creado_por=creado_por,
            grupo_id=grupo_id,
            **kwargs,
        )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"


# ---------------------------------------------------------------------------
# Entidad: PIAR (Agregado Raíz)
# ---------------------------------------------------------------------------

ESTADOS_PIAR = {"borrador", "generando_ia", "en_revision", "firmado"}


@dataclass
class Piar:
    """
    Plan Individual de Ajustes Razonables.

    Es el AGREGADO RAÍZ del dominio de inclusión educativa.
    Las características del estudiante, los ajustes razonables y las
    recomendaciones PMI solo se acceden y modifican a través de este agregado.

    Basado en: Decreto 1421 de 2017 — Anexo 2.
    """
    id: uuid.UUID
    estudiante_id: uuid.UUID
    anio_lectivo: int
    estado: str
    fecha_creacion: date
    creado_por: Optional[uuid.UUID] = None
    docentes_elaboran: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_PIAR:
            raise ValueError(f"Estado PIAR '{self.estado}' inválido.")
        if self.anio_lectivo < 2020:
            raise ValueError("El año lectivo debe ser 2020 o posterior.")

    @classmethod
    def crear(
        cls,
        estudiante_id: uuid.UUID,
        anio_lectivo: int,
        creado_por: Optional[uuid.UUID] = None,
        docentes_elaboran: Optional[str] = None,
    ) -> "Piar":
        """Crea un nuevo PIAR en estado borrador."""
        return cls(
            id=uuid.uuid4(),
            estudiante_id=estudiante_id,
            anio_lectivo=anio_lectivo,
            estado="borrador",
            fecha_creacion=date.today(),
            creado_por=creado_por,
            docentes_elaboran=docentes_elaboran,
        )

    def marcar_generando_ia(self) -> None:
        """Transición de estado cuando el agente de IA empieza a generar ajustes."""
        if self.estado != "borrador":
            raise ValueError("Solo un PIAR en borrador puede iniciar la generación IA.")
        self.estado = "generando_ia"

    def marcar_en_revision(self) -> None:
        """La IA terminó de generar; el docente puede revisar y editar."""
        if self.estado != "generando_ia":
            raise ValueError("El PIAR debe estar en estado 'generando_ia'.")
        self.estado = "en_revision"

    def firmar(self) -> None:
        """El PIAR fue firmado por todos los actores. Los ajustes razonables pueden seguir editándose."""
        if self.estado not in {"en_revision", "borrador"}:
            raise ValueError("Solo un PIAR en revisión o borrador puede firmarse.")
        self.estado = "firmado"
        self.updated_at = datetime.now(timezone.utc)

    @property
    def es_editable(self) -> bool:
        """Un PIAR puede editarse en cualquier estado."""
        return True


# ---------------------------------------------------------------------------
# Entidad: AuditoriaCambio
# ---------------------------------------------------------------------------

@dataclass
class AuditoriaCambio:
    id: uuid.UUID
    entidad_tipo: str
    entidad_id: uuid.UUID
    piar_id: uuid.UUID
    accion: str
    usuario_id: uuid.UUID
    datos_anteriores: Optional[dict] = None
    datos_nuevos: Optional[dict] = None
    fecha: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_origen: Optional[str] = None

    def __post_init__(self) -> None:
        if self.entidad_tipo not in ENTIDADES_AUDITABLES:
            raise ValueError(
                f"Tipo de entidad auditada '{self.entidad_tipo}' no válido."
            )
        if self.accion not in ACCIONES_AUDITORIA:
            raise ValueError(
                f"Acción de auditoría '{self.accion}' no válida."
            )

    @classmethod
    def crear(
        cls,
        entidad_tipo: str,
        entidad_id: uuid.UUID,
        piar_id: uuid.UUID,
        accion: str,
        usuario_id: uuid.UUID,
        datos_anteriores: Optional[dict] = None,
        datos_nuevos: Optional[dict] = None,
        ip_origen: Optional[str] = None,
    ) -> "AuditoriaCambio":
        return cls(
            id=uuid.uuid4(),
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            piar_id=piar_id,
            accion=accion,
            usuario_id=usuario_id,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_origen=ip_origen,
        )
