# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import AuditoriaCambioORM, UsuarioORM
from app.domain.entities import AuditoriaCambio
from app.domain.ports import IAuditoriaRepository


class PostgresAuditoriaRepository(IAuditoriaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entrada: AuditoriaCambio) -> AuditoriaCambio:
        orm = AuditoriaCambioORM(
            id=entrada.id,
            entidad_tipo=entrada.entidad_tipo,
            entidad_id=entrada.entidad_id,
            piar_id=entrada.piar_id,
            accion=entrada.accion,
            usuario_id=entrada.usuario_id,
            datos_anteriores=entrada.datos_anteriores,
            datos_nuevos=entrada.datos_nuevos,
            fecha=entrada.fecha,
            ip_origen=entrada.ip_origen,
        )
        self._session.add(orm)
        await self._session.flush()
        return entrada

    async def find_by_piar_id(
        self, piar_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AuditoriaCambio]:
        query = (
            select(AuditoriaCambioORM)
            .where(AuditoriaCambioORM.piar_id == piar_id)
            .options(selectinload(AuditoriaCambioORM.usuario))
            .order_by(AuditoriaCambioORM.fecha.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._session.execute(query)
        rows = result.scalars().all()
        return [_orm_to_entity(r) for r in rows]

    async def find_by_id(
        self, auditoria_id: UUID
    ) -> Optional[AuditoriaCambio]:
        query = (
            select(AuditoriaCambioORM)
            .where(AuditoriaCambioORM.id == auditoria_id)
            .options(selectinload(AuditoriaCambioORM.usuario))
        )
        result = await self._session.execute(query)
        row = result.scalars().first()
        if row is None:
            return None
        return _orm_to_entity(row)


def _orm_to_entity(orm: AuditoriaCambioORM) -> AuditoriaCambio:
    return AuditoriaCambio(
        id=orm.id,
        entidad_tipo=orm.entidad_tipo,
        entidad_id=orm.entidad_id,
        piar_id=orm.piar_id,
        accion=orm.accion,
        usuario_id=orm.usuario_id,
        datos_anteriores=orm.datos_anteriores,
        datos_nuevos=orm.datos_nuevos,
        fecha=orm.fecha,
        ip_origen=orm.ip_origen,
    )
