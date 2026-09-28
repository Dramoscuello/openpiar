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


# ---------------------------------------------------------------------------
# Setup Wizard — bootstrap token
# ---------------------------------------------------------------------------

async def require_bootstrap_token(
    x_bootstrap_token: Annotated[Optional[str], Header(alias="X-Bootstrap-Token")] = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Exige el token de instalación en los endpoints del Setup Wizard.

    - Si el sistema ya fue configurado, los endpoints de bootstrap dejan de
      existir (404) y el token queda invalidado permanentemente.
    - Si el servidor no tiene BOOTSTRAP_TOKEN configurado, rechaza con 503.
    - Si el token falta o no coincide, rechaza con 401.
    """
    result = await db.execute(
        select(ConfiguracionSistemaORM)
        .where(ConfiguracionSistemaORM.setup_completado == True)  # noqa: E712
        .limit(1)
    )
    if result.scalars().first() is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado.",
        )

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
    user_id_str = decode_access_token(token)
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
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
