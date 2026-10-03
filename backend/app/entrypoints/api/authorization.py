# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Políticas centralizadas de autorización por estudiante y PIAR.

Única fuente de verdad para decidir quién puede acceder a los datos de un
estudiante o PIAR y con qué alcance. Todos los endpoints que devuelven o
modifican información de un estudiante deben pasar por
`authorize_student_access`; las operaciones sobre un PIAR deben pasar por
`authorize_piar_access`.

Reglas (Decreto 1421 de 2017 — manejo de información sensible):

- Directivo: acceso institucional completo.
- Director de grupo: gestiona (crear, editar, eliminar) únicamente estudiantes
  de los grupos que dirige.
- Docente (aula/apoyo/orientador): lectura completa (incluye salud y hogar) de
  los estudiantes de grupos donde tenga carga académica, para fundamentar sus
  ajustes; nunca puede escribir ni eliminar el Anexo 1.
- `delete`: directivo o director del grupo del estudiante.

PIAR:

- `read`, `evidences` y `export`: directivo, director de grupo o docente con
  carga académica en el grupo.
- `edit`, `sign` y `audit_read`: directivo o director de grupo.
- `adjustments`: docente asignado a la cobertura de la asignatura.
"""

import uuid
from typing import Literal, Optional

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import (
    CargaAcademicaORM,
    EstudianteORM,
    GrupoORM,
    PiarAsignaturaORM,
    PiarORM,
)
from app.domain.entities import Usuario

AccionEstudiante = Literal["read", "write", "medical_read", "family_read", "delete"]
AccionPiar = Literal[
    "read",
    "edit",
    "adjustments",
    "evidences",
    "sign",
    "export",
    "audit_read",
]

ACCIONES_ESTUDIANTE: set[str] = {
    "read",
    "write",
    "medical_read",
    "family_read",
    "delete",
}

ACCIONES_PIAR: set[str] = {
    "read",
    "edit",
    "adjustments",
    "evidences",
    "sign",
    "export",
    "audit_read",
}

_PROPIETARIO_NO_REQUERIDO = object()


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


def puede_acceder_piar(
    accion: AccionPiar,
    *,
    es_directivo: bool,
    es_director_grupo: bool,
    tiene_carga: bool,
    es_docente_asignado: bool = False,
) -> bool:
    """Matriz pura de autorización PIAR, sin acceso a base de datos."""
    if accion not in ACCIONES_PIAR:
        raise ValueError(f"Acción de PIAR desconocida: {accion}")

    if accion == "adjustments":
        # La cobertura académica identifica al docente responsable del ajuste.
        return es_docente_asignado and (
            es_directivo or es_director_grupo or tiene_carga
        )

    if accion in {"read", "evidences", "export"}:
        return es_directivo or es_director_grupo or tiene_carga

    # Edición general, firmas internas y auditoría requieren responsabilidad
    # institucional sobre el grupo; la carga académica solo concede lectura.
    return es_directivo or es_director_grupo


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


async def _cargar_piar_para_autorizacion(
    db: AsyncSession,
    piar_id: uuid.UUID,
) -> Optional[PiarORM]:
    """Carga únicamente la relación PIAR-estudiante-grupo para autorizar."""
    result = await db.execute(
        select(PiarORM)
        .where(PiarORM.id == piar_id)
        .options(
            selectinload(PiarORM.estudiante).selectinload(EstudianteORM.grupo),
        )
    )
    return result.scalars().first()


async def _relacion_con_piar(
    db: AsyncSession,
    current_user: Usuario,
    piar: PiarORM,
) -> tuple[bool, bool]:
    """Devuelve (es_director_del_grupo, tiene_carga_en_el_grupo) del PIAR."""
    estudiante = getattr(piar, "__dict__", {}).get("estudiante")
    estudiante_id = getattr(piar, "estudiante_id", None)
    if estudiante is None or (
        estudiante_id is not None and getattr(estudiante, "grupo_id", None) is None
    ):
        if estudiante_id is not None:
            estudiante_cargado = await db.get(EstudianteORM, estudiante_id)
            if estudiante_cargado is not None:
                estudiante = estudiante_cargado

    if estudiante is None:
        return False, False

    grupo = getattr(estudiante, "__dict__", {}).get("grupo")
    grupo_id = getattr(estudiante, "grupo_id", None)
    if grupo_id is None and grupo is not None:
        grupo_id = getattr(grupo, "id", None)

    if grupo is not None:
        es_director = getattr(grupo, "director_id", None) == current_user.id
        # Evita una consulta adicional cuando la relación ya fue cargada por el
        # endpoint, sin activar una carga perezosa en AsyncSession.
        relaciones_cargadas = getattr(grupo, "__dict__", {}).get("carga", None)
        if relaciones_cargadas is not None:
            tiene_carga = any(
                getattr(carga, "docente_id", None) == current_user.id
                for carga in relaciones_cargadas
            )
            return es_director, tiene_carga
        if grupo_id is None:
            return es_director, False

    return await _relacion_con_grupo(db, current_user, grupo_id)


async def authorize_piar_access(
    db: AsyncSession,
    current_user: Usuario,
    piar_id: uuid.UUID,
    accion: AccionPiar = "read",
    *,
    piar: Optional[PiarORM] = None,
    cobertura: Optional[PiarAsignaturaORM] = None,
    propietario_id: object = _PROPIETARIO_NO_REQUERIDO,
) -> PiarORM:
    """
    Autoriza una operación sobre un PIAR.

    La autorización de PIAR combina el alcance institucional sobre el
    estudiante con reglas específicas de cobertura y autoría. Devuelve el
    PIAR para evitar una segunda consulta cuando ya fue cargado por el
    endpoint.

    - 404 si el PIAR no existe.
    - 403 si el usuario no tiene el alcance solicitado.
    """
    if accion not in ACCIONES_PIAR:
        raise ValueError(f"Acción de PIAR desconocida: {accion}")

    if piar is None:
        piar = await _cargar_piar_para_autorizacion(db, piar_id)
    if piar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PIAR no encontrado.",
        )

    if (
        propietario_id is not _PROPIETARIO_NO_REQUERIDO
        and propietario_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos sobre este recurso del PIAR.",
        )

    es_director = False
    tiene_carga = False
    if not current_user.rol.es_directivo:
        es_director, tiene_carga = await _relacion_con_piar(
            db, current_user, piar
        )

    if accion == "adjustments":
        es_docente_asignado = bool(
            cobertura is not None
            and getattr(cobertura, "docente_id", None) == current_user.id
        )
        permitido = puede_acceder_piar(
            accion,
            es_directivo=current_user.rol.es_directivo,
            es_director_grupo=es_director,
            tiene_carga=tiene_carga,
            es_docente_asignado=es_docente_asignado,
        )
        if not permitido:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el docente asignado a esta cobertura puede modificarla.",
            )
        return piar

    if not puede_acceder_piar(
        accion,
        es_directivo=current_user.rol.es_directivo,
        es_director_grupo=es_director,
        tiene_carga=tiene_carga,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este PIAR.",
        )

    return piar
