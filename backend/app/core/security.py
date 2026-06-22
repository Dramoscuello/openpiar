# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Módulo de seguridad: hash de contraseñas con bcrypt y tokens JWT.
Implementa el estándar OAuth2 Bearer para autenticación de docentes/directivos.
"""

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
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crea un token JWT con:
    - sub: identificador del usuario (UUID como string)
    - exp: fecha de expiración
    - iat: fecha de emisión

    Args:
        subject: UUID del usuario autenticado.
        expires_delta: Duración del token. Si no se provee, usa el default de settings.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodifica y valida un JWT.

    Returns:
        El 'sub' (UUID del usuario) si el token es válido.
        None si el token es inválido o expirado.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload.get("sub")
    except JWTError:
        return None
