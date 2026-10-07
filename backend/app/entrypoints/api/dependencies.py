# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Dependencias de FastAPI para OpenPiar.

Centraliza la inyección de repositorios, casos de uso y autenticación.
Esto desacopla los endpoints de las implementaciones concretas.
"""

import logging
import secrets
import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import ConfiguracionSistemaORM
from app.adapters.db.postgres.estudiante_repository import PostgresEstudianteRepository
from app.adapters.db.postgres.usuario_repository import PostgresUsuarioRepository
from app.adapters.db.postgres.auditoria_repository import PostgresAuditoriaRepository
from app.adapters.db.postgres.refresh_token_repository import PostgresRefreshTokenRepository
from app.adapters.db.session import get_db
from app.core.config import Settings, get_settings
from app.core.exceptions import SetupRequeridoError, TokenInvalidoError
from app.core.security import decode_access_token
from app.domain.entities import Usuario

logger = logging.getLogger(__name__)

# Esquema OAuth2 — apunta al endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Repositorios — se crean por request (con la sesión DB inyectada)
# ---------------------------------------------------------------------------

def get_usuario_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresUsuarioRepository:
    return PostgresUsuarioRepository(db)


def get_estudiante_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresEstudianteRepository:
    return PostgresEstudianteRepository(db)


def get_refresh_token_repo(
    db: AsyncSession = Depends(get_db),
) -> PostgresRefreshTokenRepository:
    return PostgresRefreshTokenRepository(db)


# ---------------------------------------------------------------------------
# Setup Wizard — bootstrap token
# ---------------------------------------------------------------------------

def _validar_token_bootstrap(
    x_bootstrap_token: Optional[str], settings: Settings
) -> None:
    """Valida el BOOTSTRAP_TOKEN del servidor y el presentado por el cliente."""
    if not settings.BOOTSTRAP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El servidor no tiene configurado BOOTSTRAP_TOKEN. "
                "Genera uno (openssl rand -hex 32) y reinicia el servicio."
            ),
        )

    if not x_bootstrap_token or not secrets.compare_digest(
        x_bootstrap_token, settings.BOOTSTRAP_TOKEN
    ):
        logger.warning(
            "Bootstrap rechazado: header_presente=%s, token_configurado=%s",
            x_bootstrap_token is not None and x_bootstrap_token != "",
            bool(settings.BOOTSTRAP_TOKEN),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Token de instalación inválido. Verifica que coincida exactamente "
                "con BOOTSTRAP_TOKEN de tu .env y reinicia el backend si lo editaste."
            ),
        )


async def _setup_completado(db: AsyncSession) -> bool:
    result = await db.execute(
        select(ConfiguracionSistemaORM)
        .where(ConfiguracionSistemaORM.setup_completado == True)  # noqa: E712
        .limit(1)
    )
    return result.scalars().first() is not None


async def require_bootstrap_token(
    x_bootstrap_token: Annotated[Optional[str], Header(alias="X-Bootstrap-Token")] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Exige el token de instalación en los endpoints que modifican el setup.

    - Si el sistema ya fue configurado, los endpoints de bootstrap dejan de
      existir (404) y el token queda invalidado permanentemente.
    - Si el estado no puede verificarse (BD caída), rechaza con 503 genérico.
    - Si el servidor no tiene BOOTSTRAP_TOKEN configurado, rechaza con 503.
    - Si el token falta o no coincide, rechaza con 401.
    """
    try:
        completado = await _setup_completado(db)
    except Exception as exc:
        logger.error(
            "No se pudo verificar el estado del setup (%s)", type(exc).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo verificar el estado del sistema. "
                "Revisa los logs del servidor."
            ),
        )

    if completado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado.",
        )

    _validar_token_bootstrap(x_bootstrap_token, settings)


async def require_bootstrap_token_diagnostico(
    x_bootstrap_token: Annotated[Optional[str], Header(alias="X-Bootstrap-Token")] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Variante para `POST /setup/test-db`.

    Valida el token siempre, pero si el estado del setup no puede verificarse
    porque la BD está caída, permite el diagnóstico (que es justamente su
    propósito). Si el estado es verificable y el setup ya se completó,
    responde 404 igual que el resto de endpoints de bootstrap.
    """
    _validar_token_bootstrap(x_bootstrap_token, settings)

    try:
        completado = await _setup_completado(db)
    except Exception as exc:
        logger.warning(
            "Estado del setup no verificable (%s); se permite el diagnóstico "
            "con token válido.",
            type(exc).__name__,
        )
        return

    if completado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado.",
        )


# ---------------------------------------------------------------------------
# Autenticación — usuario actual desde JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    repo: PostgresUsuarioRepository = Depends(get_usuario_repo),
) -> Usuario:
    """
    Dependencia que valida el JWT y retorna el usuario autenticado.
    Inyectar en cualquier endpoint protegido.
    """
    claims = decode_access_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(str(claims.get("sub")))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    usuario = await repo.find_by_id(user_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if int(claims.get("ver", -1)) != usuario.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada. Inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def require_directivo(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Dependencia que exige rol 'directivo'."""
    if not current_user.rol.es_directivo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere permisos de directivo.",
        )
    return current_user


# Tipos anotados para uso conveniente en firmas de funciones
CurrentUser = Annotated[Usuario, Depends(get_current_user)]
DirectivoUser = Annotated[Usuario, Depends(require_directivo)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
