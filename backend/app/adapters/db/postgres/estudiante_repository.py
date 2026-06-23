# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Repositorio PostgreSQL de Estudiantes.
Implementa el puerto IEstudianteRepository del dominio.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import EstudianteORM
from app.domain.entities import Estudiante
from app.domain.ports import IEstudianteRepository


class PostgresEstudianteRepository(IEstudianteRepository):
    """Implementación PostgreSQL del repositorio de estudiantes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -----------------------------------------------------------------------
    # Mappers
    # -----------------------------------------------------------------------

    @staticmethod
    def _to_entity(orm: EstudianteORM) -> Estudiante:
        return Estudiante(
            id=orm.id,
            nombres=orm.nombres,
            apellidos=orm.apellidos,
            tipo_documento=orm.tipo_documento,
            numero_documento=orm.numero_documento,
            fecha_nacimiento=orm.fecha_nacimiento,
            edad=orm.edad,
            lugar_nacimiento=orm.lugar_nacimiento,
            departamento_residencia=orm.departamento_residencia,
            municipio_residencia=orm.municipio_residencia,
            direccion=orm.direccion,
            barrio_vereda=orm.barrio_vereda,
            telefono=orm.telefono,
            correo=orm.correo,
            en_centro_proteccion=orm.en_centro_proteccion,
            centro_proteccion_donde=orm.centro_proteccion_donde,
            grupo_etnico=orm.grupo_etnico,
            victima_conflicto=orm.victima_conflicto,
            registro_victima=orm.registro_victima,
            creado_por=orm.creado_por,
            grupo_id=orm.grupo_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def _to_orm(estudiante: Estudiante) -> EstudianteORM:
        return EstudianteORM(
            id=estudiante.id,
            nombres=estudiante.nombres,
            apellidos=estudiante.apellidos,
            tipo_documento=estudiante.tipo_documento,
            numero_documento=estudiante.numero_documento,
            fecha_nacimiento=estudiante.fecha_nacimiento,
            edad=estudiante.edad,
            lugar_nacimiento=estudiante.lugar_nacimiento,
            departamento_residencia=estudiante.departamento_residencia,
            municipio_residencia=estudiante.municipio_residencia,
            direccion=estudiante.direccion,
            barrio_vereda=estudiante.barrio_vereda,
            telefono=estudiante.telefono,
            correo=estudiante.correo,
            en_centro_proteccion=estudiante.en_centro_proteccion,
            centro_proteccion_donde=estudiante.centro_proteccion_donde,
            grupo_etnico=estudiante.grupo_etnico,
            victima_conflicto=estudiante.victima_conflicto,
            registro_victima=estudiante.registro_victima,
            creado_por=estudiante.creado_por,
            grupo_id=estudiante.grupo_id,
        )

    # -----------------------------------------------------------------------
    # Implementación del puerto
    # -----------------------------------------------------------------------

    async def find_by_id(self, estudiante_id: uuid.UUID) -> Optional[Estudiante]:
        orm = await self._session.get(EstudianteORM, estudiante_id)
        return self._to_entity(orm) if orm else None

    async def find_by_documento(self, tipo: str, numero: str) -> Optional[Estudiante]:
        result = await self._session.execute(
            select(EstudianteORM).where(
                EstudianteORM.tipo_documento == tipo,
                EstudianteORM.numero_documento == numero.strip(),
            )
        )
        orm = result.scalars().first()
        return self._to_entity(orm) if orm else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Estudiante]:
        result = await self._session.execute(
            select(EstudianteORM)
            .order_by(EstudianteORM.apellidos, EstudianteORM.nombres)
            .offset(skip)
            .limit(limit)
        )
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def save(self, estudiante: Estudiante) -> Estudiante:
        existing = await self._session.get(EstudianteORM, estudiante.id)
        if existing:
            # Actualizar campos mutables
            for field in (
                "nombres", "apellidos", "tipo_documento", "numero_documento",
                "fecha_nacimiento", "edad", "lugar_nacimiento",
                "departamento_residencia", "municipio_residencia",
                "direccion", "barrio_vereda", "telefono", "correo",
                "en_centro_proteccion", "centro_proteccion_donde",
                "grupo_etnico", "victima_conflicto", "registro_victima",
                "grupo_id",
            ):
                setattr(existing, field, getattr(estudiante, field))
        else:
            self._session.add(self._to_orm(estudiante))

        await self._session.flush()
        return estudiante

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(EstudianteORM)
        )
        return result.scalar_one()

    async def delete_by_id(self, estudiante_id: uuid.UUID) -> bool:
        """Elimina el estudiante y todos sus datos relacionados (cascade)."""
        orm = await self._session.get(EstudianteORM, estudiante_id)
        if not orm:
            return False
        await self._session.delete(orm)
        await self._session.flush()
        return True
