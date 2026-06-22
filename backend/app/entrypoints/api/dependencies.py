# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Dependencias de FastAPI para OpenPiar.

Centraliza la inyección de repositorios, casos de uso y autenticación.
Esto desacopla los endpoints de las implementaciones concretas.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.postgres.estudiante_repository import PostgresEstudianteRepository
from app.adapters.db.postgres.usuario_repository import PostgresUsuarioRepository
from app.adapters.db.session import get_db
from app.core.config import Settings, get_settings
from app.core.exceptions import SetupRequeridoError, TokenInvalidoError
from app.core.security import decode_access_token
from app.domain.entities import Usuario

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
