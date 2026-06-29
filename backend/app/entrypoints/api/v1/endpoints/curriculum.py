# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
"""
Endpoints de Currículum — DBA y EBC.
Ruta: /api/v1/curriculum/

Proporciona búsqueda local de Derechos Básicos de Aprendizaje
y Estándares Básicos de Competencias.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import DerechoDBAORM, EstandarEBCORM
from app.adapters.db.session import get_db
from app.entrypoints.api.dependencies import CurrentUser
from app.entrypoints.api.schemas import (
    DBAListResponse,
    DBAResponse,
    EBCListResponse,
    EBCResponse,
)

router = APIRouter(prefix="/curriculum", tags=["Currículum MEN — DBA y EBC"])


@router.get(
    "/dba",
    response_model=DBAListResponse,
    summary="Buscar Derechos Básicos de Aprendizaje",
    description=(
        "Consulta los DBA del Ministerio de Educación Nacional. "
        "Filtra por grado y/o área curricular."
    ),
)
async def buscar_dba(
    grado: Optional[str] = Query(
        default=None,
        description="Grado escolar: '1', '2', ..., '11', 'transicion'",
        examples=["3", "transicion"],
    ),
    area: Optional[str] = Query(
        default=None,
        description="Área curricular: 'Matemáticas', 'Lenguaje', 'Ciencias Naturales', 'Ciencias Sociales'",
    ),
    q: Optional[str] = Query(
        default=None,
        description="Búsqueda de texto libre en el enunciado del DBA.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DBAListResponse:
    query = select(DerechoDBAORM)

    if grado:
        query = query.where(DerechoDBAORM.grado == grado)
    if area:
        query = query.where(DerechoDBAORM.area == area)
    if q:
        query = query.where(DerechoDBAORM.enunciado.ilike(f"%{q}%"))

    # Contar total antes de paginar
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginar
    query = query.order_by(DerechoDBAORM.grado, DerechoDBAORM.numero).offset(skip).limit(limit)
    result = await db.execute(query)
    items = [
        DBAResponse(
            id=r.id,
            grado=r.grado,
            area=r.area,
            numero=r.numero,
            enunciado=r.enunciado,
            evidencias=r.evidencias,
            ejemplos=r.ejemplos,
        )
        for r in result.scalars().all()
    ]

    return DBAListResponse(total=total, items=items)


@router.get(
    "/ebc",
    response_model=EBCListResponse,
    summary="Buscar Estándares Básicos de Competencias",
    description=(
        "Consulta los EBC del MEN. "
        "Filtra por rango de grados y/o área curricular."
    ),
)
async def buscar_ebc(
    rango_grados: Optional[str] = Query(
        default=None,
        description="Rango de grados: '1-3', '4-5', '6-7', '8-9', '10-11'",
    ),
    area: Optional[str] = Query(
        default=None,
        description="Área curricular",
    ),
    factor: Optional[str] = Query(
        default=None,
        description="Factor o componente del estándar",
    ),
    q: Optional[str] = Query(
        default=None,
        description="Búsqueda de texto libre en el enunciado.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> EBCListResponse:
    from sqlalchemy import func

    query = select(EstandarEBCORM)

    if rango_grados:
        query = query.where(EstandarEBCORM.rango_grados == rango_grados)
    if area:
        query = query.where(EstandarEBCORM.area == area)
    if factor:
        query = query.where(EstandarEBCORM.factor.ilike(f"%{factor}%"))
    if q:
        query = query.where(EstandarEBCORM.enunciado.ilike(f"%{q}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(EstandarEBCORM.rango_grados, EstandarEBCORM.area).offset(skip).limit(limit)
    result = await db.execute(query)
    items = [
        EBCResponse(
            id=r.id,
            rango_grados=r.rango_grados,
            area=r.area,
            factor=r.factor,
            enunciado=r.enunciado,
        )
        for r in result.scalars().all()
    ]

    return EBCListResponse(total=total, items=items)
