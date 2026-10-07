# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Servicio de sesiones persistentes con rotación de refresh tokens."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import get_settings
from app.core.security import create_refresh_token, hash_refresh_token
from app.domain.ports import IRefreshTokenRepository


class RefreshTokenInvalidoError(ValueError):
    """El refresh token no existe, expiró o fue revocado."""


class SesionService:
    """Crea, rota y revoca refresh tokens; detecta reutilización."""

    def __init__(self, repo: IRefreshTokenRepository) -> None:
        self._repo = repo
        self._settings = get_settings()

    def _expiracion(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    async def crear(
        self,
        usuario_id: uuid.UUID,
        *,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> str:
        raw, hashed = create_refresh_token()
        await self._repo.create(
            usuario_id=usuario_id,
            token_hash=hashed,
            family_id=uuid.uuid4(),
            expires_at=self._expiracion(),
            user_agent=user_agent,
            ip=ip,
        )
        return raw

    def _dentro_de_gracia(self, registro) -> bool:
        """Reuso inmediato de un token rotado (p. ej. dos pestañas a la vez)."""
        if registro.replaced_by is None or registro.revoked_at is None:
            return False
        transcurrido = datetime.now(timezone.utc) - registro.revoked_at
        return transcurrido <= timedelta(
            seconds=self._settings.REFRESH_REUSE_GRACE_SECONDS
        )

    async def rotar(
        self,
        raw_token: str,
        *,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> tuple[uuid.UUID, str]:
        registro = await self._repo.find_by_hash(hash_refresh_token(raw_token))
        if registro is None:
            raise RefreshTokenInvalidoError("Refresh token inválido.")

        if registro.revoked_at is not None:
            if self._dentro_de_gracia(registro):
                # Otra pestaña ya rotó; el cliente reintentará con la cookie nueva.
                raise RefreshTokenInvalidoError(
                    "El refresh token ya fue rotado; reintenta con el token vigente."
                )
            # Reutilización fuera de la gracia: se revoca toda la familia.
            await self._repo.revoke_family(registro.family_id)
            raise RefreshTokenInvalidoError(
                "Refresh token reutilizado; la sesión fue revocada."
            )

        if registro.expires_at <= datetime.now(timezone.utc):
            registro.revoked_at = datetime.now(timezone.utc)
            await self._repo.update(registro)
            raise RefreshTokenInvalidoError("Refresh token expirado.")

        raw_nuevo, hash_nuevo = create_refresh_token()
        nuevo = await self._repo.create(
            usuario_id=registro.usuario_id,
            token_hash=hash_nuevo,
            family_id=registro.family_id,
            expires_at=self._expiracion(),
            user_agent=user_agent,
            ip=ip,
        )
        registro.revoked_at = datetime.now(timezone.utc)
        registro.replaced_by = nuevo.id
        registro.last_used_at = registro.revoked_at
        await self._repo.update(registro)
        return registro.usuario_id, raw_nuevo

    async def revocar(self, raw_token: Optional[str]) -> None:
        if not raw_token:
            return
        registro = await self._repo.find_by_hash(hash_refresh_token(raw_token))
        if registro is None or registro.revoked_at is not None:
            return
        registro.revoked_at = datetime.now(timezone.utc)
        await self._repo.update(registro)

    async def revocar_todo(self, usuario_id: uuid.UUID) -> None:
        await self._repo.revoke_all_for_user(usuario_id)
