# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Módulo de seguridad: hash de contraseñas con bcrypt y tokens JWT.
Implementa el estándar OAuth2 Bearer para autenticación de docentes/directivos.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Contexto de hash — bcrypt con factor de trabajo auto-actualizable
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Contraseñas
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str,
    token_version: int = 0,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crea un token JWT de acceso con:
    - sub: identificador del usuario (UUID como string)
    - iss/aud: emisor y audiencia esperados
    - jti: identificador único del token
    - type: tipo de token ("access")
    - ver: versión de sesión del usuario; al incrementarla se revocan los emitidos
    - iat/exp: emisión y expiración
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": str(subject),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": uuid.uuid4().hex,
        "type": "access",
        "ver": int(token_version),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT de acceso.

    Valida firma, expiración, emisor, audiencia y tipo.

    Returns:
        El payload (claims) si el token es válido; None si no lo es.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except JWTError:
        return None

    if payload.get("type") != "access":
        return None
    return payload


def create_refresh_token() -> tuple[str, str]:
    """Genera un refresh token opaco y su hash SHA-256 para persistirlo."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    """Hash determinista del refresh token; nunca se guarda el valor original."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
