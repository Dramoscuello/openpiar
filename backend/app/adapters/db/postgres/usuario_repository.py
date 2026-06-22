# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Repositorio PostgreSQL de Usuarios.
Implementa el puerto IUsuarioRepository del dominio.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import UsuarioORM
from app.domain.entities import Usuario
from app.domain.ports import IUsuarioRepository
from app.domain.value_objects import Email, Rol


class PostgresUsuarioRepository(IUsuarioRepository):
    """Implementación PostgreSQL del repositorio de usuarios."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -----------------------------------------------------------------------
    # Mappers ORM <-> Entidad de dominio
    # -----------------------------------------------------------------------

    @staticmethod
    def _to_entity(orm: UsuarioORM) -> Usuario:
        return Usuario(
            id=orm.id,
            email=Email(orm.email),
            password_hash=orm.password_hash,
            nombre=orm.nombre,
            apellido=orm.apellido,
            rol=Rol(orm.rol),
            cargo=orm.cargo,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_orm(usuario: Usuario) -> UsuarioORM:
        return UsuarioORM(
            id=usuario.id,
            email=str(usuario.email),
            password_hash=usuario.password_hash,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            rol=str(usuario.rol),
            cargo=usuario.cargo,
            created_at=usuario.created_at,
            updated_at=usuario.updated_at,
        )

    # -----------------------------------------------------------------------
    # Implementación del puerto
    # -----------------------------------------------------------------------

    async def find_by_id(self, user_id: uuid.UUID) -> Optional[Usuario]:
        result = await self._session.execute(
            select(UsuarioORM).where(UsuarioORM.id == user_id)
        )
        orm = result.scalars().first()
        return self._to_entity(orm) if orm else None

    async def find_by_email(self, email: str) -> Optional[Usuario]:
        result = await self._session.execute(
            select(UsuarioORM).where(
                func.lower(UsuarioORM.email) == email.lower().strip()
            )
        )
        orm = result.scalars().first()
        return self._to_entity(orm) if orm else None

    async def save(self, usuario: Usuario) -> Usuario:
        # Verificar si ya existe (upsert manual)
        existing = await self._session.get(UsuarioORM, usuario.id)
        if existing:
            existing.email = str(usuario.email)
            existing.password_hash = usuario.password_hash
            existing.nombre = usuario.nombre
            existing.apellido = usuario.apellido
            existing.rol = str(usuario.rol)
            existing.cargo = usuario.cargo
            existing.updated_at = usuario.updated_at
        else:
            self._session.add(self._to_orm(usuario))

        await self._session.flush()
        return usuario

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(UsuarioORM)
        )
        return result.scalar_one()
