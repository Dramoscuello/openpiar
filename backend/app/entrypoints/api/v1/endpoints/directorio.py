# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints del Directorio de padres y acudientes.
Ruta: /api/v1/directorio/

Accesible solo para directivo o director de grupo.
Muestra solo el acudiente principal por estudiante,
con opción de compartir el PDF del acta de acuerdo.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import (
    EntornoHogarORM,
    EstudianteORM,
    GradoORM,
    GrupoORM,
    PiarORM,
)
from app.adapters.db.session import get_db
from app.entrypoints.api.authorization import subquery_grupos_dirigidos
from app.entrypoints.api.dependencies import CurrentUser
from app.entrypoints.api.schemas import (
    ContactoDirectorioOut,
    DirectorioResponse,
    EstudianteDirectorioOut,
)

router = APIRouter(prefix="/directorio", tags=["directorio"])


def _tiene_texto(columna):
    return and_(columna.is_not(None), func.trim(columna) != "")


def _expresiones_acudiente():
    """Expresiones SQL que conservan la precedencia de `_resolver_acudiente`."""
    madre = _tiene_texto(EntornoHogarORM.nombre_madre)
    padre = _tiene_texto(EntornoHogarORM.nombre_padre)
    cuidador = _tiene_texto(EntornoHogarORM.nombre_cuidador)
    madre_principal = and_(EntornoHogarORM.acudiente_principal == "madre", madre)
    padre_principal = and_(EntornoHogarORM.acudiente_principal == "padre", padre)
    cuidador_principal = and_(EntornoHogarORM.acudiente_principal == "cuidador", cuidador)

    nombre = case(
        (madre_principal, func.trim(EntornoHogarORM.nombre_madre)),
        (padre_principal, func.trim(EntornoHogarORM.nombre_padre)),
        (cuidador_principal, func.trim(EntornoHogarORM.nombre_cuidador)),
        (cuidador, func.trim(EntornoHogarORM.nombre_cuidador)),
        (madre, func.trim(EntornoHogarORM.nombre_madre)),
        (padre, func.trim(EntornoHogarORM.nombre_padre)),
        else_=None,
    )
    rol = case(
        (madre_principal, literal("madre")),
        (padre_principal, literal("padre")),
        (cuidador_principal, literal("cuidador")),
        (cuidador, literal("cuidador")),
        (madre, literal("madre")),
        (padre, literal("padre")),
        else_=None,
    )
    telefono = case(
        (madre_principal, EntornoHogarORM.telefono_madre),
        (padre_principal, EntornoHogarORM.telefono_padre),
        (cuidador_principal, EntornoHogarORM.telefono_cuidador),
        (cuidador, EntornoHogarORM.telefono_cuidador),
        (madre, EntornoHogarORM.telefono_madre),
        (padre, EntornoHogarORM.telefono_padre),
        else_=None,
    )
    correo = case(
        (madre_principal, EntornoHogarORM.correo_madre),
        (padre_principal, EntornoHogarORM.correo_padre),
        (cuidador_principal, EntornoHogarORM.correo_cuidador),
        (cuidador, EntornoHogarORM.correo_cuidador),
        (madre, EntornoHogarORM.correo_madre),
        (padre, EntornoHogarORM.correo_padre),
        else_=None,
    )
    documento = case(
        (madre_principal, func.nullif(func.trim(EntornoHogarORM.numero_documento_madre), "")),
        (padre_principal, func.nullif(func.trim(EntornoHogarORM.numero_documento_padre), "")),
        (madre, func.nullif(func.trim(EntornoHogarORM.numero_documento_madre), "")),
        (padre, func.nullif(func.trim(EntornoHogarORM.numero_documento_padre), "")),
        else_=None,
    )
    principal = case(
        (madre_principal, literal(True)),
        (padre_principal, literal(True)),
        (cuidador_principal, literal(True)),
        else_=literal(False),
    )
    return nombre, rol, telefono, correo, documento, principal


def _consulta_directorio_base(current_user: CurrentUser, q: Optional[str]):
    (
        contacto_nombre,
        contacto_rol,
        contacto_telefono,
        contacto_correo,
        contacto_documento,
        contacto_principal,
    ) = _expresiones_acudiente()
    contacto_key = case(
        (
            contacto_documento.is_not(None),
            func.concat(contacto_rol, literal("|doc|"), contacto_documento),
        ),
        else_=func.concat(
            contacto_rol,
            literal("|nombre|"),
            func.lower(func.trim(contacto_nombre)),
        ),
    )
    ultimo_piar_id = (
        select(PiarORM.id)
        .where(PiarORM.estudiante_id == EstudianteORM.id)
        .order_by(PiarORM.created_at.desc(), PiarORM.id.desc())
        .limit(1)
        .scalar_subquery()
    )

    query = (
        select(
            contacto_key.label("contact_key"),
            contacto_nombre.label("contacto_nombre"),
            contacto_rol.label("contacto_rol"),
            contacto_telefono.label("contacto_telefono"),
            contacto_correo.label("contacto_correo"),
            contacto_documento.label("contacto_documento"),
            contacto_principal.label("contacto_principal"),
            EstudianteORM.id.label("estudiante_id"),
            EstudianteORM.nombres.label("estudiante_nombres"),
            EstudianteORM.apellidos.label("estudiante_apellidos"),
            GradoORM.nombre.label("grado_nombre"),
            ultimo_piar_id.label("piar_id"),
            EstudianteORM.codigo_acceso_familia.label("codigo_acceso_familia"),
        )
        .select_from(EntornoHogarORM)
        .join(EstudianteORM, EstudianteORM.id == EntornoHogarORM.estudiante_id)
        .join(GrupoORM, GrupoORM.id == EstudianteORM.grupo_id)
        .outerjoin(GradoORM, GradoORM.id == GrupoORM.grado_id)
        .where(contacto_nombre.is_not(None))
    )

    grupos_dirigidos = subquery_grupos_dirigidos(current_user)
    if grupos_dirigidos is not None:
        query = query.where(GrupoORM.id.in_(grupos_dirigidos))

    termino = (q or "").strip()
    if termino:
        patron = f"%{termino}%"
        query = query.where(
            or_(
                contacto_nombre.ilike(patron),
                func.coalesce(contacto_documento, literal("")).ilike(patron),
                EstudianteORM.nombres.ilike(patron),
                EstudianteORM.apellidos.ilike(patron),
                EstudianteORM.numero_documento.ilike(patron),
            )
        )

    return query.cte("directorio_filtrado")


def _agrupar_contactos(rows: list) -> list[ContactoDirectorioOut]:
    contactos: dict[str, dict] = {}
    for row in rows:
        data = row._mapping if hasattr(row, "_mapping") else row
        key = data["contact_key"]
        if key not in contactos:
            contactos[key] = {
                "nombre": data["contacto_nombre"],
                "rol": data["contacto_rol"],
                "telefono": data["contacto_telefono"],
                "correo": data["contacto_correo"],
                "numero_documento": data["contacto_documento"],
                "acudiente_principal": bool(data["contacto_principal"]),
                "estudiantes": [],
            }

        contactos[key]["estudiantes"].append(
            EstudianteDirectorioOut(
                id=data["estudiante_id"],
                nombre=f"{data['estudiante_nombres']} {data['estudiante_apellidos']}",
                grado=data["grado_nombre"],
                piar_id=data["piar_id"],
                codigo_acceso_familia=data["codigo_acceso_familia"],
            )
        )

    return [ContactoDirectorioOut(**contacto) for contacto in contactos.values()]


@router.get(
    "",
    response_model=DirectorioResponse,
    summary="Listar contactos del directorio",
)
async def listar_directorio(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    q: Optional[str] = Query(default=None, max_length=100),
) -> DirectorioResponse:
    grupos_dirigidos = subquery_grupos_dirigidos(current_user)
    if grupos_dirigidos is not None:
        group_result = await db.execute(grupos_dirigidos.limit(1))
        if group_result.scalars().first() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo directivos o directores de grupo pueden acceder al directorio.",
            )

    base = _consulta_directorio_base(current_user, q)
    claves = (
        select(
            base.c.contact_key,
            func.min(func.lower(base.c.contacto_nombre)).label("orden_nombre"),
        )
        .group_by(base.c.contact_key)
        .subquery("contactos_unicos")
    )
    total_result = await db.execute(
        select(func.count()).select_from(claves)
    )
    total = total_result.scalar_one()

    claves_result = await db.execute(
        select(claves.c.contact_key)
        .order_by(claves.c.orden_nombre, claves.c.contact_key)
        .offset(skip)
        .limit(limit)
    )
    claves_pagina = claves_result.scalars().all()
    if not claves_pagina:
        return DirectorioResponse(
            contactos=[],
            total=total,
            skip=skip,
            limit=limit,
            has_next=False,
        )

    rows_result = await db.execute(
        select(base)
        .where(base.c.contact_key.in_(claves_pagina))
        .order_by(
            func.lower(base.c.contacto_nombre),
            base.c.estudiante_apellidos,
            base.c.estudiante_nombres,
        )
    )
    contactos = _agrupar_contactos(rows_result.mappings().all())
    return DirectorioResponse(
        contactos=contactos,
        total=total,
        skip=skip,
        limit=limit,
        has_next=skip + len(claves_pagina) < total,
    )
