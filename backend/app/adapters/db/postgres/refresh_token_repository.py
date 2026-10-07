# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""Repositorio PostgreSQL de refresh tokens (sesiones persistentes)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import RefreshTokenORM
from app.domain.ports import IRefreshTokenRepository, RefreshTokenData


class PostgresRefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_data(orm: RefreshTokenORM) -> RefreshTokenData:
        return RefreshTokenData(
            id=orm.id,
            usuario_id=orm.usuario_id,
            family_id=orm.family_id,
            token_hash=orm.token_hash,
            expires_at=orm.expires_at,
            revoked_at=orm.revoked_at,
            replaced_by=orm.replaced_by,
            user_agent=orm.user_agent,
            ip=orm.ip,
            last_used_at=orm.last_used_at,
        )

    async def create(
        self,
        *,
        usuario_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> RefreshTokenData:
        orm = RefreshTokenORM(
            usuario_id=usuario_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_data(orm)

    async def find_by_hash(self, token_hash: str) -> Optional[RefreshTokenData]:
        resultado = await self._session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        )
        orm = resultado.scalars().first()
        return self._to_data(orm) if orm else None

    async def update(self, token: RefreshTokenData) -> None:
        orm = await self._session.get(RefreshTokenORM, token.id)
        if orm is None:
            return
        orm.revoked_at = token.revoked_at
        orm.replaced_by = token.replaced_by
        orm.last_used_at = token.last_used_at
        await self._session.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        ahora = datetime.now(timezone.utc)
        await self._session.execute(
            update(RefreshTokenORM)
            .where(
                RefreshTokenORM.family_id == family_id,
                RefreshTokenORM.revoked_at.is_(None),
            )
            .values(revoked_at=ahora)
        )
        await self._session.flush()

    async def revoke_all_for_user(self, usuario_id: uuid.UUID) -> None:
        ahora = datetime.now(timezone.utc)
        await self._session.execute(
            update(RefreshTokenORM)
            .where(
                RefreshTokenORM.usuario_id == usuario_id,
                RefreshTokenORM.revoked_at.is_(None),
            )
            .values(revoked_at=ahora)
        )
        await self._session.flush()
