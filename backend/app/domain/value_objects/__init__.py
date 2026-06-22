# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Value Objects del dominio OpenPiar.

Los Value Objects son inmutables y se auto-validan en la construcción.
Si un valor no cumple los invariantes del dominio, se lanza un error
ANTES de que el dato corrupto entre al núcleo de la aplicación.

Patrón: dataclass frozen=True + validación en __post_init__
"""

from dataclasses import dataclass
from typing import Literal

from app.core.exceptions import ValorObjetoInvalidoError


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Email:
    """
    Correo electrónico validado.
    Longitud máxima 255 caracteres (RFC 5321).
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or "@" not in self.value:
            raise ValorObjetoInvalidoError(
                f"El correo '{self.value}' no tiene un formato válido."
            )
        if len(self.value) > 255:
            raise ValorObjetoInvalidoError(
                "El correo no puede exceder 255 caracteres."
            )

    def __str__(self) -> str:
        return self.value.lower()


# ---------------------------------------------------------------------------
# Código DANE
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodigoDANE:
    """
    Código DANE de institución educativa.
    Exactamente 12 dígitos numéricos según el estándar del MEN.
    """
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned.isdigit() or len(cleaned) != 12:
            raise ValorObjetoInvalidoError(
                f"El código DANE '{self.value}' debe tener exactamente 12 dígitos numéricos."
            )

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# NIT
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NIT:
    """
    Número de Identificación Tributaria colombiano.
    Entre 8 y 12 dígitos, puede incluir guion y dígito verificador.
    """
    value: str

    def __post_init__(self) -> None:
        # Permitir formato '900123456-7' o solo dígitos
        cleaned = self.value.replace("-", "").strip()
        if not cleaned.isdigit() or not (8 <= len(cleaned) <= 13):
            raise ValorObjetoInvalidoError(
                f"El NIT '{self.value}' no tiene un formato válido."
            )

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Número de documento de estudiante
# ---------------------------------------------------------------------------

TipoDocumento = Literal["TI", "CC", "RC", "NES", "PEP"]

TIPOS_DOCUMENTO_VALIDOS: set[str] = {"TI", "CC", "RC", "NES", "PEP"}


@dataclass(frozen=True)
class NumeroDocumento:
    """
    Documento de identidad de un estudiante.
    Combina tipo y número para garantizar unicidad semántica.

    Tipos permitidos (Decreto 1421 de 2017):
    - TI: Tarjeta de Identidad
    - CC: Cédula de Ciudadanía
    - RC: Registro Civil
    - NES: Número de Establecimiento de Salud (menores sin doc)
    - PEP: Permiso Especial de Permanencia (venezolanos)
    """
    tipo: str
    numero: str

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_DOCUMENTO_VALIDOS:
            raise ValorObjetoInvalidoError(
                f"Tipo de documento '{self.tipo}' inválido. "
                f"Debe ser uno de: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}"
            )
        numero_limpio = self.numero.strip()
        if not numero_limpio or len(numero_limpio) > 50:
            raise ValorObjetoInvalidoError(
                "El número de documento no puede estar vacío ni exceder 50 caracteres."
            )

    def __str__(self) -> str:
        return f"{self.tipo}-{self.numero}"


# ---------------------------------------------------------------------------
# Rol de usuario
# ---------------------------------------------------------------------------

RolUsuario = Literal["docente_aula", "docente_apoyo", "orientador", "directivo"]

ROLES_VALIDOS: set[str] = {"docente_aula", "docente_apoyo", "orientador", "directivo"}


@dataclass(frozen=True)
class Rol:
    """
    Rol institucional de un usuario dentro de OpenPiar.
    Determina los permisos de acceso a módulos y datos sensibles.
    """
    value: str

    def __post_init__(self) -> None:
        if self.value not in ROLES_VALIDOS:
            raise ValorObjetoInvalidoError(
                f"Rol '{self.value}' inválido. "
                f"Roles permitidos: {', '.join(ROLES_VALIDOS)}"
            )

    def __str__(self) -> str:
        return self.value

    @property
    def es_directivo(self) -> bool:
        return self.value == "directivo"

    @property
    def puede_crear_piar(self) -> bool:
        """Solo docentes de aula y de apoyo pueden crear PIARs."""
        return self.value in {"docente_aula", "docente_apoyo"}
