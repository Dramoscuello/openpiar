# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Política centralizada de autorización por estudiante.

Única fuente de verdad para decidir quién puede acceder a los datos de un
estudiante y con qué alcance. Todos los endpoints que devuelven o modifican
información de un estudiante deben pasar por `authorize_student_access`.

Reglas (Decreto 1421 de 2017 — manejo de información sensible):

- Directivo: acceso institucional completo.
- Director de grupo: gestiona (crear, editar, eliminar) únicamente estudiantes
  de los grupos que dirige.
- Docente (aula/apoyo/orientador): lectura completa (incluye salud y hogar) de
  los estudiantes de grupos donde tenga carga académica, para fundamentar sus
  ajustes; nunca puede escribir ni eliminar el Anexo 1.
- `delete`: directivo o director del grupo del estudiante.
"""

import uuid
from typing import Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    CargaAcademicaORM,
    EstudianteORM,
    GrupoORM,
)
from app.domain.entities import Usuario

AccionEstudiante = Literal["read", "write", "medical_read", "family_read", "delete"]

ACCIONES_ESTUDIANTE: set[str] = {
    "read",
    "write",
    "medical_read",
    "family_read",
    "delete",
}


def puede_acceder(
    accion: AccionEstudiante,
    *,
    es_directivo: bool,
    es_director_grupo: bool,
    tiene_carga: bool,
) -> bool:
    """Matriz pura de decisión, sin acceso a base de datos."""
    if accion not in ACCIONES_ESTUDIANTE:
        raise ValueError(f"Acción de estudiante desconocida: {accion}")

    if es_directivo:
        return True

    if accion == "read":
        return es_director_grupo or tiene_carga

    if accion == "write":
        return es_director_grupo

    if accion == "medical_read":
        return es_director_grupo or tiene_carga

    if accion == "family_read":
        return es_director_grupo or tiene_carga

    # delete: directivo o director del grupo del estudiante
    if accion == "delete":
        return es_director_grupo

    return False


def subquery_grupos_con_acceso(current_user: Usuario) -> Optional[Select]:
    """
    Subquery con los IDs de los grupos a los que el usuario tiene acceso.

    Devuelve `None` para directivos (sin restricción). Se usa en listados
    para filtrar en SQL en lugar de cargar todo y filtrar en Python.
    """
    if current_user.rol.es_directivo:
        return None

    return (
        select(GrupoORM.id)
        .outerjoin(
            CargaAcademicaORM,
            CargaAcademicaORM.grupo_id == GrupoORM.id,
        )
        .where(
            or_(
                GrupoORM.director_id == current_user.id,
                CargaAcademicaORM.docente_id == current_user.id,
            )
        )
        .distinct()
    )


async def _relacion_con_grupo(
    db: AsyncSession,
    current_user: Usuario,
    grupo_id: Optional[uuid.UUID],
) -> tuple[bool, bool]:
    """Devuelve (es_director_del_grupo, tiene_carga_en_el_grupo)."""
    if grupo_id is None:
        return False, False

    grupo = await db.get(GrupoORM, grupo_id)
    es_director = bool(grupo and grupo.director_id == current_user.id)

    carga_result = await db.execute(
        select(CargaAcademicaORM.id)
        .where(
            CargaAcademicaORM.grupo_id == grupo_id,
            CargaAcademicaORM.docente_id == current_user.id,
        )
        .limit(1)
    )
    tiene_carga = carga_result.scalars().first() is not None

    return es_director, tiene_carga


async def authorize_student_access(
    db: AsyncSession,
    current_user: Usuario,
    estudiante_id: uuid.UUID,
    accion: AccionEstudiante = "read",
    *,
    estudiante: Optional[EstudianteORM] = None,
) -> EstudianteORM:
    """
    Autoriza el acceso de `current_user` al estudiante indicado.

    - 404 si el estudiante no existe.
    - 403 si existe pero el usuario no tiene acceso para `accion`.

    Devuelve el estudiante para evitar una segunda consulta en el endpoint.
    """
    if estudiante is None:
        estudiante = await db.get(EstudianteORM, estudiante_id)
    if estudiante is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado.",
        )

    es_director = False
    tiene_carga = False
    if not current_user.rol.es_directivo:
        es_director, tiene_carga = await _relacion_con_grupo(
            db, current_user, estudiante.grupo_id
        )

    if not puede_acceder(
        accion,
        es_directivo=current_user.rol.es_directivo,
        es_director_grupo=es_director,
        tiene_carga=tiene_carga,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este estudiante.",
        )

    return estudiante


async def authorize_group_access(
    db: AsyncSession,
    current_user: Usuario,
    grupo_id: uuid.UUID,
    accion: AccionEstudiante = "write",
) -> GrupoORM:
    """
    Autoriza una acción sobre un grupo (necesario al crear un estudiante,
    cuando todavía no existe `estudiante_id`).
    """
    grupo = await db.get(GrupoORM, grupo_id)
    if grupo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El grupo seleccionado no existe.",
        )

    es_director = grupo.director_id == current_user.id
    tiene_carga = False
    if not current_user.rol.es_directivo and not es_director:
        carga_result = await db.execute(
            select(CargaAcademicaORM.id)
            .where(
                CargaAcademicaORM.grupo_id == grupo_id,
                CargaAcademicaORM.docente_id == current_user.id,
            )
            .limit(1)
        )
        tiene_carga = carga_result.scalars().first() is not None

    if not puede_acceder(
        accion,
        es_directivo=current_user.rol.es_directivo,
        es_director_grupo=es_director,
        tiene_carga=tiene_carga,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos sobre el grupo seleccionado.",
        )

    return grupo
