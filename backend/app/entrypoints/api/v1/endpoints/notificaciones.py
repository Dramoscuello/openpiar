# Copyright (c) 2026 OpenPiar Contributors — GPL-3.0
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.adapters.db.models import NotificacionORM
from app.adapters.db.session import get_db
from app.entrypoints.api.schemas import NotificacionResponse, NotificacionListResponse
from app.entrypoints.api.dependencies import CurrentUser

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("/", response_model=NotificacionListResponse)
async def listar_notificaciones(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    count_query = select(func.count(NotificacionORM.id)).where(
        NotificacionORM.usuario_id == current_user.id
    )
    count_res = await db.execute(count_query)
    total = count_res.scalar() or 0

    no_leidas_query = select(func.count(NotificacionORM.id)).where(
        NotificacionORM.usuario_id == current_user.id,
        NotificacionORM.leida == False,
    )
    no_leidas_res = await db.execute(no_leidas_query)
    no_leidas = no_leidas_res.scalar() or 0

    query = (
        select(NotificacionORM)
        .where(NotificacionORM.usuario_id == current_user.id)
        .order_by(NotificacionORM.fecha_creacion.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return NotificacionListResponse(
        total=total,
        no_leidas=no_leidas,
        items=[
            NotificacionResponse(
                id=n.id,
                usuario_id=n.usuario_id,
                tipo=n.tipo,
                titulo=n.titulo,
                mensaje=n.mensaje,
                recurso_url=n.recurso_url,
                leida=n.leida,
                fecha_creacion=n.fecha_creacion,
                fecha_lectura=n.fecha_lectura,
            )
            for n in items
        ],
    )


@router.get("/no-leidas/count")
async def contar_no_leidas(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    query = select(func.count(NotificacionORM.id)).where(
        NotificacionORM.usuario_id == current_user.id,
        NotificacionORM.leida == False,
    )
    result = await db.execute(query)
    count = result.scalar() or 0
    return {"no_leidas": count}


@router.patch("/{notificacion_id}/leer", response_model=NotificacionResponse)
async def marcar_leida(
    notificacion_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    notif = await db.get(NotificacionORM, notificacion_id)
    if not notif or notif.usuario_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")

    from datetime import datetime, timezone
    notif.leida = True
    notif.fecha_lectura = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(notif)

    return NotificacionResponse(
        id=notif.id,
        usuario_id=notif.usuario_id,
        tipo=notif.tipo,
        titulo=notif.titulo,
        mensaje=notif.mensaje,
        recurso_url=notif.recurso_url,
        leida=notif.leida,
        fecha_creacion=notif.fecha_creacion,
        fecha_lectura=notif.fecha_lectura,
    )


@router.patch("/leer-todas")
async def marcar_todas_leidas(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    await db.execute(
        update(NotificacionORM)
        .where(
            NotificacionORM.usuario_id == current_user.id,
            NotificacionORM.leida == False,
        )
        .values(leida=True, fecha_lectura=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"success": True}
