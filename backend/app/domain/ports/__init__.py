# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Puertos (interfaces abstractas) del dominio OpenPiar.

Los puertos definen los contratos que el núcleo de dominio espera.
Las implementaciones concretas (PostgreSQL, InMemory) viven
en app/adapters/ e implementan estas interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.entities import AuditoriaCambio, Estudiante, Piar, Usuario


# ---------------------------------------------------------------------------
# Puerto: Repositorio de Usuarios
# ---------------------------------------------------------------------------

class IUsuarioRepository(ABC):
    """Contrato para persistencia de usuarios del sistema."""

    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[Usuario]:
        """Busca un usuario por su UUID."""
        ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[Usuario]:
        """Busca un usuario por email (case-insensitive)."""
        ...

    @abstractmethod
    async def save(self, usuario: Usuario) -> Usuario:
        """Persiste un usuario nuevo o actualiza uno existente."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Retorna el total de usuarios registrados."""
        ...


# ---------------------------------------------------------------------------
# Puerto: Repositorio de Refresh Tokens (sesiones)
# ---------------------------------------------------------------------------

@dataclass
class RefreshTokenData:
    """Registro de sesión persistente; nunca contiene el token en claro."""
    id: UUID
    usuario_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    replaced_by: Optional[UUID] = None
    user_agent: Optional[str] = None
    ip: Optional[str] = None
    last_used_at: Optional[datetime] = None


class IRefreshTokenRepository(ABC):
    """Contrato para persistir y revocar refresh tokens con rotación."""

    @abstractmethod
    async def create(
        self,
        *,
        usuario_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> RefreshTokenData:
        ...

    @abstractmethod
    async def find_by_hash(self, token_hash: str) -> Optional[RefreshTokenData]:
        """Busca por hash, incluidos los revocados, para detectar reutilización."""
        ...

    @abstractmethod
    async def update(self, token: RefreshTokenData) -> None:
        ...

    @abstractmethod
    async def revoke_family(self, family_id: UUID) -> None:
        ...

    @abstractmethod
    async def revoke_all_for_user(self, usuario_id: UUID) -> None:
        ...


# ---------------------------------------------------------------------------
# Puerto: Repositorio de Estudiantes
# ---------------------------------------------------------------------------

class IEstudianteRepository(ABC):
    """Contrato para persistencia de estudiantes y sus entornos (Anexo 1)."""

    @abstractmethod
    async def find_by_id(self, estudiante_id: UUID) -> Optional[Estudiante]:
        ...

    @abstractmethod
    async def find_by_documento(
        self, tipo: str, numero: str
    ) -> Optional[Estudiante]:
        """Busca por tipo + número de documento (llave de negocio)."""
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Estudiante]:
        ...

    @abstractmethod
    async def save(self, estudiante: Estudiante) -> Estudiante:
        ...

    @abstractmethod
    async def count(self) -> int:
        ...


# ---------------------------------------------------------------------------
# Puerto: Repositorio de PIARs
# ---------------------------------------------------------------------------

class IPiarRepository(ABC):
    """Contrato para persistencia del PIAR y sus componentes (Anexo 2)."""

    @abstractmethod
    async def find_by_id(self, piar_id: UUID) -> Optional[Piar]:
        ...

    @abstractmethod
    async def find_by_estudiante(self, estudiante_id: UUID) -> list[Piar]:
        """Lista todos los PIARs de un estudiante."""
        ...

    @abstractmethod
    async def save(self, piar: Piar) -> Piar:
        ...


# ---------------------------------------------------------------------------
# Puerto: Agente Pedagógico de IA
# ---------------------------------------------------------------------------

class IAgentePedagogico(ABC):
    """
    Contrato para el agente de IA que genera ajustes razonables DUA.

    Implementaciones posibles:
    - GeminiAgentAdapter: Usa la API de Google Gemini
    - MockAgentAdapter: Para tests unitarios sin IA real
    """

    @abstractmethod
    async def generar_ajustes_dua(
        self,
        perfil_estudiante: dict,
        objetivo_curricular: dict,
        perfil_pei: dict,
    ) -> dict:
        """
        Genera una propuesta de ajustes razonables DUA en JSON estructurado.

        Args:
            perfil_estudiante: Datos del Anexo 1 (salud, hogar, trayectoria).
            objetivo_curricular: DBA o EBC seleccionado por el docente.
            perfil_pei: Modelo pedagógico y valores del colegio extraídos del PEI.

        Returns:
            dict con campos: representacion, accion_expresion, implicacion,
            barreras_identificadas, ajustes_evaluacion.
        """
        ...

    @abstractmethod
    async def extraer_perfil_pei(self, texto_pei: str) -> dict:
        """
        Analiza el texto del PEI y extrae el perfil pedagógico institucional.

        Returns:
            dict con: modelo_pedagogico, enfoques_didacticos, valores, politicas_convivencia.
        """
        ...


# ---------------------------------------------------------------------------
# Puerto: Repositorio de Auditoría
# ---------------------------------------------------------------------------

class IAuditoriaRepository(ABC):
    """Contrato para persistencia del registro de auditoría de cambios."""

    @abstractmethod
    async def save(self, entrada: AuditoriaCambio) -> AuditoriaCambio:
        """Persiste una entrada de auditoría."""
        ...

    @abstractmethod
    async def find_by_piar_id(
        self, piar_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditoriaCambio]:
        """Lista entradas de auditoría para un PIAR específico."""
        ...

    @abstractmethod
    async def find_by_id(self, auditoria_id: UUID) -> Optional[AuditoriaCambio]:
        """Busca una entrada de auditoría por su ID."""
        ...
